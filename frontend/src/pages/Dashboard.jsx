import { useEffect, useState } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { getStockoutRisk, getDeadStockReport } from "../api";

const RISK_COLORS = { HIGH: "#dc2626", MEDIUM: "#d97706", LOW: "#16a34a" };
const CLASS_COLORS = {
  FAST_MOVING: "#16a34a",
  NORMAL: "#4f46e5",
  SLOW_MOVING: "#d97706",
  DEAD_STOCK: "#dc2626",
  OUT_OF_STOCK: "#64748b",
};

function formatINR(n) {
  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export default function Dashboard({ onLogout }) {
  const [stockout, setStockout] = useState(null);
  const [deadStock, setDeadStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [s, d] = await Promise.all([getStockoutRisk(), getDeadStockReport()]);
        setStockout(s);
        setDeadStock(d);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div style={styles.center}>Loading dashboard...</div>;
  if (error) return <div style={styles.center}>{error}</div>;

  const pieData = Object.entries(deadStock.summary)
    .filter(([, v]) => v.count > 0)
    .map(([k, v]) => ({ name: k.replace("_", " "), value: v.value, key: k }));

  const barData = Object.entries(deadStock.summary).map(([k, v]) => ({
    name: k.replace("_", " "),
    count: v.count,
    key: k,
  }));

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.h1}>Smart Inventory & Demand Forecasting ERP</h1>
        <button style={styles.logoutBtn} onClick={onLogout}>Log out</button>
      </header>

      {/* KPI Cards */}
      <div style={styles.kpiRow}>
        <KpiCard label="Total Inventory Value" value={formatINR(deadStock.total_inventory_value)} accent="#4f46e5" />
        <KpiCard label="Recoverable Capital (Dead/Slow Stock)" value={formatINR(deadStock.recoverable_capital_estimate)} accent="#dc2626" />
        <KpiCard label="High Stockout Risk Items" value={stockout.high_risk_count} accent="#dc2626" />
        <KpiCard label="Medium Stockout Risk Items" value={stockout.medium_risk_count} accent="#d97706" />
      </div>

      {/* Charts */}
      <div style={styles.chartRow}>
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Inventory Value by Classification</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={(e) => e.name}>
                {pieData.map((entry) => (
                  <Cell key={entry.key} fill={CLASS_COLORS[entry.key]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatINR(v)} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Product Count by Classification</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count">
                {barData.map((entry) => (
                  <Cell key={entry.key} fill={CLASS_COLORS[entry.key]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stockout Risk Table */}
      <div style={styles.panel}>
        <h3 style={styles.panelTitle}>Stockout Risk — Reorder Recommendations</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>SKU</th>
              <th style={styles.th}>Product</th>
              <th style={styles.th}>Stock</th>
              <th style={styles.th}>Avg Weekly Demand</th>
              <th style={styles.th}>Days Left</th>
              <th style={styles.th}>Risk</th>
              <th style={styles.th}>Recommended Order</th>
            </tr>
          </thead>
          <tbody>
            {stockout.items.map((item) => (
              <tr key={item.product_id}>
                <td style={styles.td}>{item.sku}</td>
                <td style={styles.td}>{item.product_name}</td>
                <td style={styles.td}>{item.current_stock}</td>
                <td style={styles.td}>{item.avg_weekly_demand}</td>
                <td style={styles.td}>{item.days_of_stock ?? "—"}</td>
                <td style={styles.td}>
                  <span style={{ ...styles.badge, background: RISK_COLORS[item.stockout_risk] }}>
                    {item.stockout_risk}
                  </span>
                </td>
                <td style={styles.td}>{item.recommended_order_qty > 0 ? item.recommended_order_qty : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Dead Stock Table */}
      <div style={styles.panel}>
        <h3 style={styles.panelTitle}>Dead Stock & Overstock Intelligence</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>SKU</th>
              <th style={styles.th}>Product</th>
              <th style={styles.th}>Stock</th>
              <th style={styles.th}>Days of Stock</th>
              <th style={styles.th}>Classification</th>
              <th style={styles.th}>Value Tied Up</th>
              <th style={styles.th}>Recommended Action</th>
            </tr>
          </thead>
          <tbody>
            {deadStock.items.map((item) => (
              <tr key={item.product_id}>
                <td style={styles.td}>{item.sku}</td>
                <td style={styles.td}>{item.product_name}</td>
                <td style={styles.td}>{item.current_stock}</td>
                <td style={styles.td}>{item.days_of_stock ?? "—"}</td>
                <td style={styles.td}>
                  <span style={{ ...styles.badge, background: CLASS_COLORS[item.classification] }}>
                    {item.classification.replace("_", " ")}
                  </span>
                </td>
                <td style={styles.td}>{formatINR(item.holding_value)}</td>
                <td style={{ ...styles.td, fontSize: "12px", color: "#475569" }}>{item.recommended_action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KpiCard({ label, value, accent }) {
  return (
    <div style={{ ...styles.kpiCard, borderTop: `3px solid ${accent}` }}>
      <div style={styles.kpiValue}>{value}</div>
      <div style={styles.kpiLabel}>{label}</div>
    </div>
  );
}

const styles = {
  page: { fontFamily: "'Inter', system-ui, sans-serif", background: "#f8fafc", minHeight: "100vh", padding: "24px 32px" },
  center: { display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", fontFamily: "sans-serif", color: "#475569" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" },
  h1: { fontSize: "20px", fontWeight: 700, color: "#0f172a", margin: 0 },
  logoutBtn: { padding: "8px 16px", borderRadius: "8px", border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", fontSize: "13px" },
  kpiRow: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "24px" },
  kpiCard: { background: "#fff", padding: "18px 20px", borderRadius: "12px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" },
  kpiValue: { fontSize: "24px", fontWeight: 700, color: "#0f172a" },
  kpiLabel: { fontSize: "12px", color: "#64748b", marginTop: "4px" },
  chartRow: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px" },
  panel: { background: "#fff", borderRadius: "12px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)", marginBottom: "24px" },
  panelTitle: { fontSize: "14px", fontWeight: 600, color: "#0f172a", margin: "0 0 16px" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: "13px" },
  th: { textAlign: "left", padding: "8px 10px", borderBottom: "2px solid #e2e8f0", color: "#64748b", fontWeight: 600, fontSize: "11px", textTransform: "uppercase" },
  td: { padding: "10px", borderBottom: "1px solid #f1f5f9", color: "#1e293b" },
  badge: { padding: "3px 10px", borderRadius: "999px", color: "#fff", fontSize: "11px", fontWeight: 600 },
};
