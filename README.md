# ORBIT — E-Commerce Customer Segmentation & Recommendation Analysis

A notebook-free, local-first web application that converts online retail transaction data into customer segments and product ideas. The interface is a custom HTML/CSS/JavaScript dashboard; the analysis is performed in Python.

## What the application does

- Cleans retail transaction data by removing incomplete rows, cancellations, non-positive quantities, and invalid prices.
- Builds customer-level **RFM features**: Recency, Frequency, and Monetary value.
- Applies `log1p` transformation and `StandardScaler` feature scaling.
- Uses **K-Means** to create four behaviour-based customer clusters.
- Calculates an elbow curve and a sample silhouette score as model diagnostics.
- Produces a 2D customer-cluster chart and customer segment profiles.
- Uses **cosine similarity** on customer-product purchase profiles to recommend products a selected customer has not purchased.
- Exports the cleaned transactions, customer feature table, and segment profile as CSV files.
- Runs locally in a browser; no account, API key, Jupyter Notebook, Flask, Streamlit, or paid service is required for local use.

## Project files

All source files and the included dataset are in this one project folder.

| File | Purpose |
|---|---|
| `app.py` | Python HTTP server and API endpoints |
| `analytics.py` | Cleaning, RFM engineering, K-Means, charts, and cosine-similarity recommendations |
| `index.html` | Dashboard structure |
| `styles.css` | Responsive ORBIT visual design |
| `app.js` | Dashboard interactions and API calls |
| `online_retail_sample.csv` | Included synthetic demo transaction data |
| `requirements.txt` | Required Python libraries |
| `smoke_test.py` | Quick analysis and recommendation test |
| `render.yaml`, `Procfile` | Optional deployment configuration |
| `GITHUB_STEPS.md` | Terminal-first GitHub publishing steps |
| `DEPLOYMENT_AND_ROLLBACK.md` | Optional deployment and rollback guidance |

The app creates these output files in the same folder after the first run:

- `cleaned_transactions.csv`
- `customer_segments.csv`
- `segment_profiles.csv`
- `segment_scatter.png`
- `segment_mix.png`
- `elbow_curve.png`

## 1. Requirements

- Windows 10/11
- Python 3.10 or newer, available through the `py` command
- Git for Windows only when you are ready to publish to GitHub
- Internet access for the first-time Python package installation

## 2. Run the project from Windows Terminal

**Do not open Jupyter Notebook.** Use PowerShell or the VS Code Terminal.

1. Download and extract the ZIP. Open the extracted folder `ecommerce_customer_segmentation_recommender`.
2. In File Explorer, open that folder. Click the address bar, type `powershell`, and press Enter. This opens PowerShell in the correct project folder.
3. Check Python:

   ```powershell
   py --version
   ```

4. Create a project-specific virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run this once in the same terminal and activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

6. Install the listed libraries:

   ```powershell
   py -m pip install --upgrade pip
   py -m pip install -r requirements.txt
   ```

7. Run the quick project test:

   ```powershell
   py smoke_test.py
   ```

   You should see `SMOKE TEST PASSED` near the bottom.

8. Start the web application:

   ```powershell
   py app.py
   ```

9. Open this address in Chrome:

   **http://127.0.0.1:8000**

10. Keep the terminal open while using the app. To stop it, click the terminal and press **CTRL + C**.

### If port 8000 is already in use

In the same PowerShell window, run:

```powershell
$env:PORT = "8001"
py app.py
```

Then open `http://127.0.0.1:8001`.

## 3. Use the included dataset or import UCI Online Retail

The ZIP includes `online_retail_sample.csv`, a **synthetic demonstration dataset** created for this project. It is not the original UCI data. It contains realistic retail-style customer, invoice, product, date, quantity, price, and country fields, plus a few deliberately invalid rows to demonstrate the cleaning process.

To use the original dataset recommended in the assignment:

1. Open the official [UCI Online Retail dataset page](https://archive.ics.uci.edu/dataset/352/online+retail).
2. Download `Online Retail.xlsx` from UCI.
3. Open the workbook in a spreadsheet application and use **Save As → CSV UTF-8 (Comma delimited)**. Keep the original column headers.
4. Start the ORBIT app and click **Import CSV** in the top-right corner.
5. Select the saved CSV. The app validates it, rebuilds the RFM table and K-Means model, refreshes the charts, and updates the dashboard.

Required transaction columns are `InvoiceNo`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, and either `Description` or `StockCode`. The app also reads `Country` when it is present. The importer accepts common variations in column names, such as `Invoice`, `Qty`, `Date`, `Price`, and `Customer`.

The imported CSV is saved locally as `uploaded_transactions.csv` and is ignored by Git so you do not accidentally publish a large or private upload. The demo dataset remains unchanged in `online_retail_sample.csv`.

## 4. How the analysis works

1. **Cleaning:** missing identifiers, invalid dates, cancellation invoices (invoice numbers beginning with `C`), zero/negative quantities, and zero/negative prices are excluded.
2. **RFM:** Recency is measured in days since the customer's latest purchase; Frequency is the count of distinct invoices; Monetary is the sum of valid line totals.
3. **Preprocessing:** `log1p` reduces skew in RFM values; `StandardScaler` puts the features on comparable scales.
4. **Segmentation:** K-Means with a fixed random seed groups customers into four clusters. Cluster IDs are mapped to business-friendly names by comparing cluster-level RFM profiles: Champions, Regular Customers, Occasional Buyers, and At-Risk Customers. These labels are interpretations of the unsupervised clusters, not pre-existing labels in the source data.
5. **Diagnostics:** the elbow chart compares inertia values for multiple K choices; the silhouette score is calculated on a sample when possible.
6. **Recommendations:** cosine similarity compares each customer's product-purchase vector with other customers. Products purchased by similar customers but not yet purchased by the selected customer become suggestions.

## 5. Outputs and screenshots for submission

After the first successful launch, confirm the generated CSV and PNG output files appear in the same project folder. Useful screenshots for your project record:

- ORBIT dashboard overview with the four KPI cards.
- Customer segment cards and the customer directory.
- Product studio showing generated recommendations for a selected customer.
- Transaction page and the cleaned dataset export.
- Terminal showing `py smoke_test.py` passed and `py app.py` running.
- Public GitHub repository page after the push.

## 6. GitHub and deployment

Follow the terminal sequence in [GITHUB_STEPS.md](GITHUB_STEPS.md). Optional Render deployment is described in [DEPLOYMENT_AND_ROLLBACK.md](DEPLOYMENT_AND_ROLLBACK.md); `render.yaml` is included at the repository root.

## Dataset attribution

The optional original dataset is **Online Retail** by Daqing Chen, hosted by the UCI Machine Learning Repository, DOI: [10.24432/C5BW33](https://doi.org/10.24432/C5BW33), licensed under CC BY 4.0. The included demo CSV is synthetic and does not contain records copied from the UCI dataset.

## Troubleshooting

- **`py` is not recognized:** install Python from [python.org](https://www.python.org/downloads/windows/) and enable the Python launcher during setup. Close and reopen PowerShell.
- **`ModuleNotFoundError`:** activate `.venv` and rerun `py -m pip install -r requirements.txt`.
- **Charts are missing:** stop the server with CTRL+C, confirm dependencies installed, then run `py app.py` again. The charts are generated when analysis starts.
- **CSV upload says columns are missing:** check the required column names in the import dialog and save the file as CSV UTF-8.
- **Need to return to demo data:** stop the app, delete `uploaded_transactions.csv` from the project folder, then run `py app.py` again.
