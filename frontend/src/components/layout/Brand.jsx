import { Link } from "react-router-dom";
export default function Brand({ light = false, showIcon = true }) {
  return (
    <Link
      to="/"
      aria-label="RescueSync, inicio"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        textDecoration: "none",
        color: light ? "white" : "var(--ink)",
        fontWeight: 750,
        fontSize: "1.3rem",
        letterSpacing: "-.04em",
      }}
    >
      {showIcon && <svg
        width="34"
        height="38"
        viewBox="0 0 34 38"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M17 2 31 7v11c0 9-8 15-14 18C11 33 3 27 3 18V7L17 2Z"
          stroke="currentColor"
          strokeWidth="2"
        />
        <path d="M17 10v15M9.5 17.5h15" stroke="currentColor" strokeWidth="3" />
      </svg>}
      <span>
        Rescue
        <span style={{ color: light ? "#a3dfc9" : "var(--primary)" }}>
          Sync
        </span>
      </span>
    </Link>
  );
}
