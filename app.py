import copy
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Velocity Banking & Debt Payoff Simulator", layout="wide"
)

st.title("⚡ Debt Payoff & Velocity Banking Simulator")
st.markdown("""
This app simulates paying off debts using a **Line of Credit (LOC)** chunking strategy (Velocity Banking)
versus traditional monthly payoff methods.
""")

# ==========================================
# 1. CASH FLOW & INCOME SECTION
# ==========================================
st.sidebar.header("1. Cash Flow & Income")

monthly_income = st.sidebar.number_input(
    "Monthly Take-Home Income ($)", min_value=0.0, value=12000.0, step=100.0
)

monthly_expenses = st.sidebar.number_input(
    "Monthly Living Expenses ($) [Excluding Debt]",
    min_value=0.0,
    value=4889.0,
    step=100.0,
)

living_expenses = monthly_expenses

net_surplus = max(0.0, monthly_income - living_expenses)

st.sidebar.metric(
    label="Net Surplus Available Funds",
    value=f"${net_surplus:,.2f}",
    help=(
        "Monthly cash flow available for minimum debt payments, LOC chunking,"
        " and principal paydowns."
    ),
)

st.sidebar.divider()
st.sidebar.header("2. Line of Credit (LOC) Settings")
loc_limit = st.sidebar.number_input(
    "LOC Total Limit ($)", value=200000.0, step=5000.0
)
loc_interest_rate = (
    st.sidebar.number_input(
        "LOC Annual Interest Rate (%)", value=6.2, step=0.1
    )
    / 100.0
)
loc_current_balance = st.sidebar.number_input(
    "Current LOC Balance ($)", value=127000.0, step=1000.0
)
max_chunk_ratio = (
    st.sidebar.slider("Max % of LOC Limit to use for a Chunk", 20, 95, 95) / 100.0
)
safety_buffer = st.sidebar.number_input(
    "Safety Buffer / Emergency Reserve ($)", value=1000.0, step=100.0
)

st.sidebar.header("3. Priority Strategy Selection")
strategy_mode = st.sidebar.selectbox(
    "Select Strategy Option",
    [
        "Auto-Select Best Strategy (Compare All)",
        "Highest Interest First (Avalanche)",
        "Lowest Balance First (Snowball)",
        "Highest Payment First (Cash-Flow Boost)",
    ],
)

# ==========================================
# MAIN PAGE: DEBT INPUTS
# ==========================================
st.subheader("Your Current Debts & Loans")

default_debts = [
    {
        "name": "GREEN LOAN",
        "balance": 28600.0,
        "rate": 1.00,
        "min_pay": 195.58,
        "fixed_lock_months": 36,
    },
    {
        "name": "RECLADDING LOAN",
        "balance": 120000.0,
        "rate": 5.89,
        "min_pay": 1102.75,
        "fixed_lock_months": 0,
    },
]

if "debts" not in st.session_state:
  st.session_state.debts = default_debts

df_input = pd.DataFrame(st.session_state.debts)
edited_df = st.data_editor(
    df_input,
    num_rows="dynamic",
    column_config={
        "name": st.column_config.TextColumn("Debt Name", required=True),
        "balance": st.column_config.NumberColumn(
            "Current Balance ($)", min_value=0.0, format="$%.2f"
        ),
        "rate": st.column_config.NumberColumn(
            "Interest Rate (%)", min_value=0.0, format="%.2f%%"
        ),
        "min_pay": st.column_config.NumberColumn(
            "Minimum Payment ($)", min_value=0.0, format="$%.2f"
        ),
        "fixed_lock_months": st.column_config.SelectboxColumn(
            "Fixed Lock (Months)",
            options=[0, 12, 24, 36, 48, 60],
            required=True,
            help=(
                "Number of months before lump-sum payoff is allowed without"
                " penalty."
            ),
        ),
    },
    use_container_width=True,
)

debts_list = edited_df.to_dict("records")

# ==========================================
# LOAN PAYMENT CALCULATOR TABLE
# ==========================================
st.subheader("🧮 Amortized Monthly Payment Calculator")
st.markdown(
    "Calculate required monthly payments based on loan balances, interest"
    " rates, and desired payoff terms."
)

default_calc = [
    {
        "Loan Name": "LOC",
        "Loan Total ($)": 127000.0,
        "Interest Rate (%)": 5.89,
        "Payment Type": "INT ONLY",
        "Term (Years)": 25,
    },
    {
        "Loan Name": "GREEN LOAN",
        "Loan Total ($)": 28600.0,
        "Interest Rate (%)": 1.00,
        "Payment Type": "P&I",
        "Term (Years)": 25,
    },
    {
        "Loan Name": "RECLADDING LOAN",
        "Loan Total ($)": 120000.0,
        "Interest Rate (%)": 5.89,
        "Payment Type": "P&I",
        "Term (Years)": 25,
    },
]

df_calc_input = pd.DataFrame(default_calc)
edited_calc_df = st.data_editor(
    df_calc_input,
    num_rows="dynamic",
    column_config={
        "Loan Name": st.column_config.TextColumn("Loan Name", required=True),
        "Loan Total ($)": st.column_config.NumberColumn(
            "Loan Total ($)", min_value=0.0, format="$%.2f"
        ),
        "Interest Rate (%)": st.column_config.NumberColumn(
            "Interest Rate (%)", min_value=0.0, format="%.2f%%"
        ),
        "Payment Type": st.column_config.SelectboxColumn(
            "Payment Type",
            options=["P&I", "INT ONLY"],
            required=True,
            help="Select Principal & Interest or Interest-Only payment mode.",
        ),
        "Term (Years)": st.column_config.NumberColumn(
            "Term (Years)", min_value=1, max_value=40, format="%d yrs"
        ),
    },
    use_container_width=True,
)

calc_results = []
for _, row in edited_calc_df.iterrows():
  p = row["Loan Total ($)"]
  annual_r = row["Interest Rate (%)"] / 100.0
  pay_type = row.get("Payment Type", "P&I")
  years = int(row["Term (Years)"])

  monthly_payment = 0.0
  total_interest = 0.0
  total_paid = 0.0

  if p > 0:
    if pay_type == "INT ONLY":
      monthly_payment = (p * annual_r) / 12.0
      total_interest = 0.0
      total_paid = p
    else:
      if years > 0:
        if annual_r == 0:
          monthly_payment = p / (years * 12)
        else:
          i = annual_r / 12.0
          n = years * 12
          monthly_payment = p * (i * (1 + i) ** n) / ((1 + i) ** n - 1)

        total_paid = monthly_payment * (years * 12)
        total_interest = total_paid - p

  calc_results.append({
      "Loan Name": row["Loan Name"],
      "Loan Total ($)": round(p, 2),
      "Interest Rate (%)": round(row["Interest Rate (%)"], 2),
      "Payment Type": pay_type,
      "Term (Years)": "-" if pay_type == "INT ONLY" else years,
      "Calculated Monthly Payment ($)": round(monthly_payment, 2),
      "Total Interest ($)": 0.0 if pay_type == "INT ONLY" else round(total_interest, 2),
      "Total Cost ($)": round(p if pay_type == "INT ONLY" else total_paid, 2),
  })

df_results = pd.DataFrame(calc_results)
st.dataframe(df_results, use_container_width=True)

if not df_results.empty:
  total_combined_principal = df_results["Loan Total ($)"].sum()
  total_combined_interest = df_results["Total Interest ($)"].sum()

  col_sum1, col_sum2 = st.columns(2)
  col_sum1.metric(
      label="Total Loan Principal Value",
      value=f"${total_combined_principal:,.2f}",
      help="Sum of loan balances/totals listed in the calculator table.",
  )
  col_sum2.metric(
      label="Total Combined Traditional Interest",
      value=f"${total_combined_interest:,.2f}",
      help="Sum of total interest across all amortized loans listed above.",
  )


# ==========================================
# SIMULATION ENGINE FUNCTIONS
# ==========================================
def sort_debts(debts, strategy):
  if strategy == "Highest Payment First (Cash-Flow Boost)":
    return sorted(debts, key=lambda x: x["min_pay"], reverse=True)
  elif strategy == "Highest Interest First (Avalanche)":
    return sorted(debts, key=lambda x: x["rate"], reverse=True)
  elif strategy == "Lowest Balance First (Snowball)":
    return sorted(debts, key=lambda x: x["balance"])
  return debts


def run_velocity_simulation(
    debts_input,
    income,
    expenses,
    loc_limit,
    loc_rate,
    loc_start_bal,
    max_chunk_pct,
    buffer,
    strategy,
):
  debts = copy.deepcopy(debts_input)
  for d in debts:
    d["rate"] = d["rate"] / 100.0

  loc_bal = loc_start_bal
  max_chunk_allowed = loc_limit * max_chunk_pct

  month = 0
  max_months = 360
  logs = []

  total_interest_debts = 0.0
  total_interest_loc = 0.0

  while month < max_months:
    month += 1

    active_debts = [d for d in debts if d["balance"] > 0.01]
    if not active_debts and loc_bal <= 0.01:
      break

    total_min_payments = sum(d["min_pay"] for d in active_debts)
    monthly_cash_flow = income - expenses - total_min_payments

    if monthly_cash_flow < 0:
      st.error(
          f"Month {month}: Expenses and Minimum Payments exceed Monthly Income!"
          " Positive cash flow is required."
      )
      return None

    for d in active_debts:
      lock_months = d.get("fixed_lock_months", 0)
      if month == lock_months and d["balance"] > 0.01:
        rem_bal = d["balance"]
        d["balance"] = 0
        loc_bal += rem_bal

    unlocked_debts = [
        d
        for d in active_debts
        if d["balance"] > 0.01 and month > d.get("fixed_lock_months", 0)
    ]
    unlocked_debts = sort_debts(unlocked_debts, strategy)

    loc_available = max_chunk_allowed - loc_bal
    if loc_available > 500 and unlocked_debts:
      target_debt = unlocked_debts[0]
      chunk_amount = min(target_debt["balance"], loc_available)

      if chunk_amount > 0:
        target_debt["balance"] -= chunk_amount
        loc_bal += chunk_amount

    loc_interest_month = (loc_bal * loc_rate) / 12.0
    total_interest_loc += loc_interest_month
    loc_bal += loc_interest_month

    paydown_to_loc = min(monthly_cash_flow, loc_bal)
    loc_bal -= paydown_to_loc
    remaining_cash_flow = monthly_cash_flow - paydown_to_loc

    for d in active_debts:
      monthly_interest = (d["balance"] * d["rate"]) / 12.0
      total_interest_debts += monthly_interest
      d["balance"] += monthly_interest

      pay = min(d["min_pay"], d["balance"])
      d["balance"] -= pay

      if (
          remaining_cash_flow > 0
          and unlocked_debts
          and d == unlocked_debts[0]
      ):
        extra = min(remaining_cash_flow, d["balance"])
        d["balance"] -= extra
        remaining_cash_flow -= extra

    total_debt_bal = sum(d["balance"] for d in debts)

    logs.append({
        "Month": month,
        "Total Debt Balance": round(total_debt_bal, 2),
        "LOC Balance": round(loc_bal, 2),
        "Combined Balance": round(total_debt_bal + loc_bal, 2),
        "Monthly Cash Flow": round(monthly_cash_flow, 2),
        "Interest Paid (LOC)": round(total_interest_loc, 2),
        "Interest Paid (Debts)": round(total_interest_debts, 2),
        "Total Interest Paid": round(
            total_interest_loc + total_interest_debts, 2
        ),
    })

  return pd.DataFrame(logs)


# ==========================================
# RUN SIMULATION & DISPLAY RESULTS
# ==========================================
if st.button("🚀 Run Payoff Simulation", type="primary"):
  if not debts_list:
    st.warning("Please add at least one debt item above.")
  else:
    strategies_to_test = [
        "Highest Interest First (Avalanche)",
        "Lowest Balance First (Snowball)",
        "Highest Payment First (Cash-Flow Boost)",
    ]

    all_results = {}
    summary_data = []

    for strat in strategies_to_test:
      res_df = run_velocity_simulation(
          copy.deepcopy(debts_list),
          monthly_income,
          living_expenses,
          loc_limit,
          loc_interest_rate,
          loc_current_balance,
          max_chunk_ratio,
          safety_buffer,
          strat,
      )
      if res_df is not None and not res_df.empty:
        all_results[strat] = res_df
        summary_data.append({
            "Strategy": strat,
            "Months to Debt-Free": res_df["Month"].max(),
            "Total Interest Paid ($)": res_df["Total Interest Paid"].max(),
            "Final Monthly Cash Flow ($)": res_df["Monthly Cash Flow"].iloc[-1],
        })

    summary_df = pd.DataFrame(summary_data)

    if not summary_df.empty:
      best_row = summary_df.loc[summary_df["Total Interest Paid ($)"].idxmin()]
      best_strategy = best_row["Strategy"]

      st.markdown("---")
      st.subheader("📊 Strategy Results & Auto-Selection")

      st.success(
          f"🏆 **Optimal Strategy Auto-Selected:** {best_strategy} "
          f"(Total Interest: ${best_row['Total Interest Paid ($)']:,.2f} | "
          f"Timeline: {best_row['Months to Debt-Free']} Months)"
      )

      st.dataframe(
          summary_df.style.format({
              "Total Interest Paid ($)": "${:,.2f}",
              "Final Monthly Cash Flow ($)": "${:,.2f}",
          }),
          use_container_width=True,
      )

      active_strat = (
          best_strategy
          if strategy_mode == "Auto-Select Best Strategy (Compare All)"
          else strategy_mode
      )
      results_df = all_results.get(
          active_strat, list(all_results.values())[0]
      )

      total_months = results_df["Month"].max()
      total_interest = results_df["Total Interest Paid"].max()

      m1, m2, m3 = st.columns(3)
      m1.metric(
          "Debt-Free Timeline",
          f"{total_months} Months",
          f"{round(total_months/12, 1)} Years",
      )
      m2.metric("Total Interest Paid", f"${total_interest:,.2f}")
      m3.metric(
          "Final Monthly Cash Flow",
          f"${results_df['Monthly Cash Flow'].iloc[-1]:,.2f}",
      )

      fig = go.Figure()
      fig.add_trace(
          go.Scatter(
              x=results_df["Month"],
              y=results_df["Total Debt Balance"],
              name="Traditional Debts Balance",
              line=dict(color="orange", width=2),
          )
      )
      fig.add_trace(
          go.Scatter(
              x=results_df["Month"],
              y=results_df["LOC Balance"],
              name="Line of Credit Balance",
              line=dict(color="firebrick", width=2, dash="dash"),
          )
      )
      fig.add_trace(
          go.Scatter(
              x=results_df["Month"],
              y=results_df["Combined Balance"],
              name="Total Combined Liability",
              line=dict(color="green", width=3),
          )
      )

      fig.update_layout(
          title=f"Debt Paydown & LOC Chunking Trajectory ({active_strat})",
          xaxis_title="Months",
          yaxis_title="Balance ($)",
          hovermode="x unified",
          template="plotly_white",
      )
      st.plotly_chart(fig, use_container_width=True)

      with st.expander("🔍 View Month-by-Month Amortization Schedule"):
        st.dataframe(results_df, use_container_width=True)

      st.markdown("---")
      st.subheader("💡 Strategic Debt Payoff Analysis")
      st.info("""
**Execution Strategy:**

* **Primary Focus:** Prioritize paying down higher-interest debts first (such as the 5.89% Recladding Loan) using your monthly cash flow surplus swept directly into the Line of Credit to minimize daily compounding interest.
* **Fixed Lock Management:** Keep fixed-term loans running on minimum payments during lock-in periods to avoid early repayment penalties. Once fixed terms expire (e.g., reaching Month 36 on a 3-year fixed loan), lump-sum chunk payments or full roll-overs into the line of credit should be executed.
* **Low-Interest Debts:** Maintain base payments on ultra-low rate debts (e.g., 1.00% Loan) until higher-rate loans and LOC balances are fully cleared.
        """)
