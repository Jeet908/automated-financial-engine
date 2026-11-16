from setuptools import setup, find_packages

setup(
    name="financial-engine",
    version="1.0.0",
    description="Production-ready, 100% zero-touch Automated Financial Modeling & Valuation Engine",
    author="Principal Financial Architect & Quantitative Engineer",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "openpyxl>=3.1.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "pytest-cov>=4.0.0"],
        "analytics": ["numpy>=1.22.0", "pandas>=1.5.0", "scipy>=1.9.0"],
    },
    entry_points={
        "console_scripts": [
            "financial-engine=financial_engine.cli:main",
        ],
    },
)
