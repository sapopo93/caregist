import { ImageResponse } from "next/og";

export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(135deg, #2C1A0E 0%, #5C3317 55%, #C8862A 100%)",
          color: "#F5F0E8",
          padding: "64px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 28, letterSpacing: 4, textTransform: "uppercase", color: "#F2C96B" }}>
          CareGist
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 860 }}>
          <div style={{ fontSize: 64, lineHeight: 1.05, fontWeight: 700 }}>
            The intelligence layer for UK care-provider data
          </div>
          <div style={{ fontSize: 28, lineHeight: 1.3, color: "#E8E0D0" }}>
            Daily-refreshed regulatory data for dashboard, exports, monitoring, and API workflows.
          </div>
        </div>
        <div style={{ display: "flex", gap: 18, fontSize: 24, color: "#E8E0D0" }}>
          <span>55,818 providers</span>
          <span>Updated daily</span>
          <span>Dashboard + exports + API</span>
        </div>
      </div>
    ),
    size,
  );
}
