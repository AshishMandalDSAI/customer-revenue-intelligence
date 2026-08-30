<div align="center">

# 🚀 NovaMart Customer 360

### Customer Revenue Intelligence Platform (CRIP)

**AI-Powered Customer Analytics • Churn Prediction • CLV • Revenue-at-Risk • Profitability • Next-Best-Action**

<p>
  <a href="YOUR_STREAMLIT_URL_HERE">
    <img src="https://img.shields.io/badge/🚀%20LIVE%20DEMO-OPEN%20DASHBOARD-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo"/>
  </a>
  <a href="https://github.com/AshishMandalDSAI/MarketPulse-AI">
    <img src="https://img.shields.io/badge/GitHub-SOURCE%20CODE-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
  </a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python"/>
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi"/>
  <img src="https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square&logo=streamlit"/>
  <img src="https://img.shields.io/badge/Scikit--Learn-ML-F7931E?style=flat-square&logo=scikit-learn"/>
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=flat-square&logo=postgresql"/>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker"/>
  <img src="https://img.shields.io/badge/Power%20BI-Analytics-F2C811?style=flat-square&logo=powerbi"/>
</p>

<p>
  <b>Turn customer data into revenue decisions.</b>
</p>

</div>

---

## 🌟 What is NovaMart Customer 360?

**NovaMart Customer 360** is an end-to-end **Customer Revenue Intelligence Platform** designed to transform customer and transaction data into actionable business decisions.

The platform combines:

- 🎯 Customer 360 analytics
- 🔥 Churn prediction
- 💰 Customer Lifetime Value (CLV)
- ⚠️ Revenue-at-Risk analysis
- 📊 Customer profitability
- 🧩 RFM analysis & segmentation
- 🤖 Next-Best-Action recommendations
- 🧠 AI Analytics Copilot
- 🚀 FastAPI REST backend
- 📈 Interactive Streamlit dashboard
- 📊 Power BI-ready datasets
- 🐘 PostgreSQL database design
- 🐳 Docker & Docker Compose
- 🧪 Automated pytest validation

The project uses a **synthetic e-commerce dataset** created specifically for academic and portfolio demonstration.

> ⚠️ **Disclaimer:** NovaMart is a fictional company and the dataset is synthetic. The results are intended for academic/project demonstration and should not be interpreted as real business performance.

---

# 🚀 Live Demo

<div align="center">

### Try the platform directly in your browser

<a href="YOUR_STREAMLIT_URL_HERE">

<img src="https://img.shields.io/badge/🚀%20LAUNCH%20LIVE%20DEMO-NovaMart%20Customer%20360-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" width="360"/>

</a>

<br><br>

**No installation required. Explore the interactive dashboard online.**

</div>

---

# 🎯 Business Problem

Modern e-commerce businesses generate huge volumes of customer, order, payment, product, campaign, and interaction data.

The challenge is not simply collecting this data.

The real challenge is answering:

> **Which customers are at risk, which customers are valuable, how much revenue is at risk, and what should the business do next?**

NovaMart Customer 360 addresses these questions through an integrated analytics and machine-learning platform.

### Key business questions

| Business Question | Platform Solution |
|---|---|
| Which customers may churn? | Churn Prediction |
| Which customers are most valuable? | CLV Prediction |
| How much revenue is at risk? | Revenue-at-Risk |
| Which customers are profitable? | Profitability Analytics |
| How are customers segmented? | RFM + Segmentation |
| What action should we take? | Next-Best-Action |
| Can management explore insights interactively? | Streamlit Dashboard |
| Can analysts consume predictions programmatically? | FastAPI |
| Can executives use BI tools? | Power BI Exports |
| Can decision-makers ask questions? | AI Copilot |

---

# 🧠 Platform Architecture

```text
                    ┌─────────────────────────────┐
                    │     Synthetic E-Commerce    │
                    │          Dataset             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   Data Validation & Cleaning │
                    │ Feature Engineering + RFM    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │   ML Analytics   │          │ Business Analytics│
          ├──────────────────┤          ├──────────────────┤
          │ Churn Prediction │          │ Segmentation     │
          │ CLV Prediction   │          │ Profitability     │
          │ Explainability   │          │ Revenue-at-Risk  │
          └────────┬─────────┘          └────────┬─────────┘
                   │                             │
                   └──────────────┬──────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │   Next-Best-Action Engine   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ Streamlit        │          │ FastAPI          │
          │ Executive        │          │ REST API         │
          │ Dashboard        │          │                  │
          └────────┬─────────┘          └────────┬─────────┘
                   │                             │
                   ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ AI Analytics     │          │ External Apps /  │
          │ Copilot          │          │ Integrations     │
          └──────────────────┘          └──────────────────┘

                         ┌──────────────────────┐
                         │      Power BI        │
                         │ Executive Analytics  │
                         └──────────────────────┘
