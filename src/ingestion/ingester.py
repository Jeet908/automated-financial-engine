"""
UniversalIngester: reads financial files in multiple formats (.xlsx, .xls,
.csv, .json, .pdf) and returns a NormalizedFinancials instance.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from src.ingestion.detector import StandardDetector
from src.ingestion.normalizer import DataNormalizer, NormalizedFinancials


class UniversalIngester:
    """
    Reads a financial data file and returns canonical NormalizedFinancials.

    Supported formats
    -----------------
    .xlsx / .xls  — pandas read_excel (requires openpyxl)
    .csv          — pandas read_csv
    .json         — json.load → DataFrame
    .pdf          — table extraction via PyMuPDF (fitz); install hint if missing
    """

    def __init__(self) -> None:
        self._detector  = StandardDetector()
        self._normalizer = DataNormalizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_file(self, file_path: str) -> NormalizedFinancials:
        """
        Load ``file_path``, auto-detect accounting conventions, normalise,
        and return a :class:`NormalizedFinancials` instance.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the financial data file.

        Returns
        -------
        NormalizedFinancials
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix in {".xlsx", ".xls"}:
            df = self._read_excel(path)
        elif suffix == ".csv":
            df = self._read_csv(path)
        elif suffix == ".json":
            df = self._read_json(path)
        elif suffix == ".pdf":
            df = self._read_pdf(path)
        else:
            raise ValueError(
                f"Unsupported file format '{suffix}'. "
                "Supported: .xlsx, .xls, .csv, .json, .pdf"
            )

        df = self._sanitize(df)
        return self._detect_and_normalize(df)

    def ingest_dataframe(self, df: pd.DataFrame) -> NormalizedFinancials:
        """Ingest an already-loaded DataFrame (useful for testing)."""
        df = self._sanitize(df)
        return self._detect_and_normalize(df)

    # ------------------------------------------------------------------
    # Private readers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_excel(path: Path) -> pd.DataFrame:
        """
        Read the first sheet from an Excel workbook.
        Intelligently handles client ERP quirks:
        - Blank top rows
        - Merged title banner rows
        - Trailing footnote rows
        """
        import re
        raw = pd.read_excel(path, sheet_name=0, header=None, dtype=str)
        if raw.empty:
            return raw

        date_col_pattern = re.compile(
            r"(fy\s*\d{2,4}|20\d{2}|19\d{2}|q[1-4]|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-/\s]?\d{2,4}|\d{1,2}[-/](mar|dec|jun|sep|\d{1,2})[-/]\d{2,4})",
            re.IGNORECASE
        )
        label_pattern = re.compile(
            r"(particular|line item|description|account|ledger|metric|statement|item|parameter)",
            re.IGNORECASE
        )

        header_row_idx = 0
        best_score = -1
        max_scan = min(25, len(raw))

        for r_idx in range(max_scan):
            row_vals = [
                str(x).strip() for x in raw.iloc[r_idx]
                if pd.notna(x) and str(x).strip() not in ("", "nan", "None", "NaN")
            ]
            if len(row_vals) < 2:
                continue

            score = 0
            for val in row_vals:
                if date_col_pattern.search(val):
                    score += 3
                if label_pattern.search(val):
                    score += 4

            if score > best_score and score >= 3:
                best_score = score
                header_row_idx = r_idx

        banner_parts = []
        if best_score >= 3:
            # Capture any title or ERP banner text that appeared before the header
            for b_idx in range(header_row_idx):
                for cell in raw.iloc[b_idx]:
                    if pd.notna(cell) and str(cell).strip() not in ("", "nan", "None", "NaN"):
                        banner_parts.append(str(cell).strip())

            headers = [
                str(h).strip() if pd.notna(h) and str(h).strip() not in ("", "nan", "None")
                else f"col_{i}"
                for i, h in enumerate(raw.iloc[header_row_idx])
            ]
            df = raw.iloc[header_row_idx + 1:].copy()
            df.columns = headers
        else:
            df = pd.read_excel(path, sheet_name=0, header=0, dtype=str)

        # Attach banner text
        if banner_parts:
            df.attrs["banner_text"] = " ".join(banner_parts)

        # Drop trailing footnote rows
        footnote_pattern = re.compile(
            r"^(\*|note\s*\d*|source|generated|confidential|---|prepared by|tallyprime|zoho books)",
            re.IGNORECASE
        )
        valid_indices = []
        for idx, row in df.iterrows():
            first_val = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ""
            if footnote_pattern.search(first_val):
                continue
            valid_indices.append(idx)

        df = df.loc[valid_indices].reset_index(drop=True)
        return df

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig")

    @staticmethod
    def _read_json(path: Path) -> pd.DataFrame:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)

        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try common shapes: {"data": [...]} or orient=records/index/columns
            if "data" in data and isinstance(data["data"], list):
                return pd.DataFrame(data["data"])
            # orient=columns → {col: {index: value}}
            try:
                return pd.DataFrame.from_dict(data)
            except ValueError:
                return pd.DataFrame([data])
        else:
            raise ValueError(f"Cannot parse JSON structure: {type(data)}")

    @staticmethod
    def _read_pdf(path: Path) -> pd.DataFrame:
        """Extract tables from a PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF ingestion.\n"
                "Install it with: pip install PyMuPDF\n"
                "(Restart the Python interpreter after installation.)"
            ) from exc

        doc = fitz.open(str(path))
        all_rows: list = []

        for page in doc:
            # find_tables is available in PyMuPDF >= 1.23
            if hasattr(page, "find_tables"):
                tables = page.find_tables()
                for table in tables.tables:
                    rows = table.extract()
                    all_rows.extend(rows)
            else:
                # Fallback: extract raw text blocks as rows
                text = page.get_text("text")
                for line in text.split("\n"):
                    if line.strip():
                        all_rows.append([line.strip()])

        doc.close()

        if not all_rows:
            raise ValueError(f"No tables found in PDF: {path}")

        # Determine header from first row
        headers = [str(h) if h else f"col_{i}" for i, h in enumerate(all_rows[0])]
        rows    = all_rows[1:]

        # Pad/truncate rows to match header length
        n = len(headers)
        padded = [
            (row + [""] * n)[:n] for row in rows
        ]
        return pd.DataFrame(padded, columns=headers)

    # ------------------------------------------------------------------
    # Detection + normalization
    # ------------------------------------------------------------------

    def _detect_and_normalize(self, df: pd.DataFrame) -> NormalizedFinancials:
        standard   = self._detector.detect_accounting_standard(df)
        currency_info = self._detector.detect_currency_unit(df)
        fy_info    = self._detector.detect_fiscal_year(df)

        detection_result: Dict[str, Any] = {
            "standard":      standard,
            "currency":      currency_info["currency"],
            "unit":          currency_info["unit"],
            "multiplier":    currency_info["multiplier"],
            "fy_end_month":  fy_info["fy_end_month"],
            "periodicity":   fy_info["periodicity"],
            "columns":       fy_info["columns"],
        }

        return self._normalizer.normalize(df, detection_result)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize(df: pd.DataFrame) -> pd.DataFrame:
        """
        Basic cleanup:
        - Strip whitespace from string cells and column names
        - Replace empty strings with None
        - Drop completely empty rows/columns
        - Preserve metadata attributes (attrs)
        """
        attrs = getattr(df, "attrs", {}).copy()
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(x).strip() if isinstance(x, str) else x
            )
            df[col] = df[col].replace({"": None, "nan": None, "NaN": None, "None": None})

        df = df.dropna(how="all").dropna(axis=1, how="all")
        df = df.reset_index(drop=True)
        df.attrs = attrs
        return df
