import {
  Bell,
  ChevronDown,
  Grid2X2,
  Search,
  Sun,
  Moon,
  Workflow,
  ArrowLeftRight,
  IndianRupee,
  Users,
  ShieldAlert,
  Flame,
} from "lucide-react";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Pie,
  PieChart,
  Cell,
  Tooltip,
  YAxis,
} from "recharts";

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import "../styles/dashboard.css";
import Sidebar from "../components/Sidebar";


const trendData = [
  { day: "1", value: 10300 },
  { day: "2", value: 10500 },
  { day: "3", value: 11900 },
  { day: "4", value: 10400 },
  { day: "5", value: 12200 },
  { day: "6", value: 10800 },
  { day: "7", value: 10600 },
  { day: "8", value: 10700 },
  { day: "9", value: 10400 },
  { day: "10", value: 10500 },
  { day: "11", value: 10200 },
  { day: "12", value: 9500 },
  { day: "13", value: 9600 },
  { day: "14", value: 9800 },
  { day: "15", value: 9000 },
  { day: "16", value: 9100 },
  { day: "17", value: 9200 },
  { day: "18", value: 9000 },
  { day: "19", value: 9300 },
  { day: "20", value: 10200 },
  { day: "21", value: 9000 },
  { day: "22", value: 9100 },
  { day: "23", value: 10100 },
  { day: "24", value: 10800 },
  { day: "25", value: 11100 },
  { day: "26", value: 11200 },
  { day: "27", value: 10500 },
  { day: "28", value: 11100 },
  { day: "29", value: 10600 },
  { day: "30", value: 11400 },
];


const riskData = [
  { name: "Low", value: 10240 },
  { name: "Medium", value: 1750 },
  { name: "High", value: 380 },
  { name: "Critical", value: 110 },
];


const kpis = [
  {
    title: "Total accounts",
    value: "12,480",
    change: "+4.2%",
    icon: Users,
    type: "blue",
  },
  {
    title: "Total transactions",
    value: "3,07,809",
    change: "+8.6%",
    icon: ArrowLeftRight,
    type: "blue",
  },
  {
    title: "Total transaction amount",
    value: "₹525 Cr",
    change: "+6.1%",
    icon: IndianRupee,
    type: "blue",
  }
  
];


export default function Dashboard() {

  const navigate = useNavigate();

  const [dark, setDark] = useState(true);


  const goToAlerts = () => {
    console.log("Alerts clicked");
    navigate("/alerts");
  };


  return (
    <div
      className={
        dark
          ? "dashboard dark-dashboard"
          : "dashboard light-dashboard"
      }
    >

      {/* SIDEBAR */}

      <aside className="sidebar">


        <div className="workspace-title">
          WORKSPACE
        </div>


        {/* NAVIGATION */}

        <nav className="sidebar-nav">

          {/* DASHBOARD */}

          <button
            type="button"
            className="nav-item active"
            onClick={() => navigate("/dashboard")}
          >

            <Grid2X2 size={20} />

            <span>
              Dashboard
            </span>

            <span className="nav-dot" />

          </button>


          {/* ALERTS */}

          <button
            type="button"
            className="nav-item"
            onClick={goToAlerts}
          >

            <Bell size={20} />

            <span>
              Alerts
            </span>

          </button>


          {/* INVESTIGATIONS */}

          <button
            type="button"
            className="nav-item"
            onClick={() => {
              console.log("Investigations clicked");
            }}
          >

            <Workflow size={20} />

            <span>
              Investigations
            </span>

          </button>

        </nav>


        {/* DATASET */}

        <div className="active-dataset">

          <div className="dataset-label">
            ACTIVE DATASET
          </div>

          <div className="dataset-name">
            Project_Vigilance_Dataset_...
          </div>

          <div className="dataset-info">
            2,84,912 records · 25.56 MB
          </div>

        </div>

      </aside>


      {/* MAIN */}

      <main className="dashboard-main">

        {/* HEADER */}

        <header className="dashboard-header">

          <div>

            <h1>
              Dashboard
            </h1>

            <p>
              Dataset ·
              Project_Vigilance_Dataset_Password_Protected.xlsx
            </p>

          </div>


          <div className="header-actions">

            <div className="header-search">

              <Search size={20} />

              <input
                placeholder="Search account ID..."
              />

            </div>


            <button className="header-icon">

              <Bell size={21} />

            </button>


            <button
              className="header-icon"
              onClick={() =>
                setDark((value) => !value)
              }
            >

              {dark ? (
                <Sun size={21} />
              ) : (
                <Moon size={21} />
              )}

            </button>

          </div>

        </header>


        {/* CONTENT */}

        <div className="dashboard-content">

          {/* FILTERS */}

          <section className="filter-bar">

            <FilterButton text="Last 30 days" />
            <FilterButton text="All risk levels" />
            <FilterButton text="All channels" />
            <FilterButton text="All patterns" />
            <FilterButton text="All locations" />

            <div className="account-filter">

              <Search size={18} />

              <input
                placeholder="Account ID"
              />

            </div>

          </section>


          {/* KPI */}

          <section className="kpi-grid">

            {kpis.map(
              ({
                title,
                value,
                change,
                icon: Icon,
                type,
              }) => (

                <div
                  className="kpi-card"
                  key={title}
                >

                  <div className="kpi-top">

                    <div
                      className={`kpi-icon ${type}`}
                    >
                      <Icon size={21} />
                    </div>

                    <div className="kpi-change">
                      ↗ {change}
                    </div>

                  </div>


                  <div className="kpi-value">
                    {value}
                  </div>


                  <div className="kpi-title">
                    {title}
                  </div>

                </div>

              )
            )}

          </section>


          {/* CHARTS */}

          <section className="charts-grid">

            <div className="chart-card trend-card">

              <div className="chart-header">

                <div>

                  <h2>
                    Transaction trend
                  </h2>

                  <p>
                    Daily transaction activity
                    across the dataset
                  </p>

                </div>

              </div>


              <div className="trend-chart">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <AreaChart data={trendData}>

                    <defs>

                      <linearGradient
                        id="transactionFill"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >

                        <stop
                          offset="0%"
                          stopColor="#7191ff"
                          stopOpacity={0.18}
                        />

                        <stop
                          offset="100%"
                          stopColor="#7191ff"
                          stopOpacity={0}
                        />

                      </linearGradient>

                    </defs>

                    <YAxis
                      domain={[3500, 14000]}
                      tick={{
                        fill: "#7890b8",
                        fontSize: 12,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <Tooltip />

                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#7191ff"
                      strokeWidth={2.5}
                      fill="url(#transactionFill)"
                    />

                  </AreaChart>

                </ResponsiveContainer>

              </div>

            </div>


            <div className="chart-card risk-card">

              <div className="chart-header">

                <div>

                  <h2>
                    Risk distribution
                  </h2>

                  <p>
                    Accounts by risk level
                  </p>

                </div>

              </div>


              <div className="risk-chart">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <PieChart>

                    <Pie
                      data={riskData}
                      dataKey="value"
                      innerRadius={74}
                      outerRadius={108}
                    >

                      <Cell fill="#11bd8b" />
                      <Cell fill="#ffae16" />
                      <Cell fill="#ff7d1c" />
                      <Cell fill="#e93959" />

                    </Pie>

                  </PieChart>

                </ResponsiveContainer>

                <div className="risk-center">

                  <strong>
                    12.5K
                  </strong>

                  <span>
                    accounts
                  </span>

                </div>

              </div>

            </div>

          </section>

        </div>

      </main>

    </div>
  );
}


function FilterButton({
  text,
}: {
  text: string;
}) {

  return (
    <button className="filter-button">
      {text}
      <ChevronDown size={17} />
    </button>
  );
}