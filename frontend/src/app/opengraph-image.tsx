import { ImageResponse } from "next/og";

export const alt = "KpopWins, K-pop music show wins since 2014";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "center",
        background: "#ff3d81",
        color: "#241526",
        display: "flex",
        height: "100%",
        justifyContent: "center",
        padding: "72px",
        width: "100%",
      }}
    >
      <div style={{ border: "8px solid #241526", boxShadow: "18px 18px 0 #241526", display: "flex", flexDirection: "column", padding: "54px 64px", width: "100%" }}>
        <div style={{ color: "white", display: "flex", fontSize: 84, fontWeight: 800, letterSpacing: "-3px" }}>KpopWins</div>
        <div style={{ display: "flex", fontSize: 42, fontWeight: 700, marginTop: 20 }}>K-pop music show wins since 2014</div>
      </div>
    </div>,
    size,
  );
}
