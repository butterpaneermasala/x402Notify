import { useState, useEffect, useRef } from "react";
import "./index.css";

// Gateway URL - set via environment variable for deployment
const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "http://localhost:3000";
// Developer agent service (server-side) - demo will call this service to have the agent pay & send
const DEV_SERVICE_URL = import.meta.env.VITE_DEV_SERVICE_URL || "http://localhost:8001";

export default function App() {
    const [subscribed, setSubscribed] = useState(false);
    const [chatId, setChatId] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [price, setPrice] = useState(3500);
    const [priceHistory, setPriceHistory] = useState<number[]>([3500, 3520, 3480, 3510, 3490]);
    const [notifications, setNotifications] = useState<string[]>([]);
    const [wasInRange, setWasInRange] = useState(true);
    const [showSdkInfo, setShowSdkInfo] = useState(false);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const LOW_THRESHOLD = 3000;
    const HIGH_THRESHOLD = 4000;

    useEffect(() => {
        if (!subscribed) return;

        const interval = setInterval(() => {
            setPrice((prev) => {
                const volatility = 80;
                let change = (Math.random() - 0.5) * volatility * 2;
                const center = 3500;
                change += (center - prev) * 0.1;

                if (Math.random() < 0.08) {
                    change = Math.random() > 0.5 ? 200 : -200;
                }

                let newPrice = Math.round(prev + change);
                newPrice = Math.max(2500, Math.min(4500, newPrice));

                setPriceHistory((h) => [...h, newPrice].slice(-30));

                const inRange = newPrice >= LOW_THRESHOLD && newPrice <= HIGH_THRESHOLD;

                if (wasInRange && !inRange) {
                    if (newPrice < LOW_THRESHOLD) {
                        triggerNotification(newPrice, "dropped below $3,000");
                    } else {
                        triggerNotification(newPrice, "surged above $4,000");
                    }
                }
                setWasInRange(inRange);

                return newPrice;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [subscribed, chatId, wasInRange]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const width = canvas.width;
        const height = canvas.height;
        const padding = 50;

        ctx.fillStyle = "#0f0f1a";
        ctx.fillRect(0, 0, width, height);

        if (priceHistory.length < 2) return;

        const maxPrice = 4500;
        const minPrice = 2500;
        const priceRange = maxPrice - minPrice;

        const lowY = height - padding - ((LOW_THRESHOLD - minPrice) / priceRange) * (height - padding * 2);
        const highY = height - padding - ((HIGH_THRESHOLD - minPrice) / priceRange) * (height - padding * 2);

        ctx.fillStyle = "rgba(239, 68, 68, 0.1)";
        ctx.fillRect(padding, lowY, width - padding - 20, height - padding - lowY);
        ctx.fillStyle = "rgba(34, 197, 94, 0.1)";
        ctx.fillRect(padding, padding, width - padding - 20, highY - padding);

        ctx.strokeStyle = "rgba(239, 68, 68, 0.5)";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(padding, lowY);
        ctx.lineTo(width - 20, lowY);
        ctx.stroke();

        ctx.strokeStyle = "rgba(34, 197, 94, 0.5)";
        ctx.beginPath();
        ctx.moveTo(padding, highY);
        ctx.lineTo(width - 20, highY);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.beginPath();
        const isBelow = price < LOW_THRESHOLD;
        const isAbove = price > HIGH_THRESHOLD;
        ctx.strokeStyle = isBelow ? "#ef4444" : isAbove ? "#22c55e" : "#fff";
        ctx.lineWidth = 2;

        priceHistory.forEach((p, i) => {
            const x = padding + (i / (priceHistory.length - 1 || 1)) * (width - padding - 20);
            const y = height - padding - ((p - minPrice) / priceRange) * (height - padding * 2);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        const lastX = padding + ((priceHistory.length - 1) / (priceHistory.length - 1 || 1)) * (width - padding - 20);
        const lastY = height - padding - ((price - minPrice) / priceRange) * (height - padding * 2);
        ctx.beginPath();
        ctx.fillStyle = isBelow ? "#ef4444" : isAbove ? "#22c55e" : "#fff";
        ctx.arc(lastX, lastY, 5, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#666";
        ctx.font = "11px Inter";
        ctx.textAlign = "right";
        ctx.fillText("$4,500", padding - 8, padding + 4);
        ctx.fillStyle = "#22c55e";
        ctx.fillText("$4,000", padding - 8, highY + 4);
        ctx.fillStyle = "#ef4444";
        ctx.fillText("$3,000", padding - 8, lowY + 4);
        ctx.fillStyle = "#666";
        ctx.fillText("$2,500", padding - 8, height - padding + 4);

    }, [priceHistory, price]);

    const triggerNotification = async (newPrice: number, action: string) => {
        const emoji = action.includes("dropped") ? "🔻" : "🚀";
        const message = `${emoji} <b>ETH ${action}!</b>\n\n💰 Current: <b>$${newPrice.toLocaleString()}</b>\n⏰ ${new Date().toLocaleTimeString()}\n\n<i>— Whale Watcher via x402-Notify</i>`;

        setNotifications((n) => [...n, `⏳ x402: Requesting agent to send...`]);

        try {
            // Ask the agent service to send the message; the agent will sign/pay and call the gateway.
            const res = await fetch(`${DEV_SERVICE_URL}/send/${encodeURIComponent(chatId)}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message }),
            });

            if (res.ok) {
                setNotifications((n) => [...n.slice(0, -1), `✅ Agent paid & Delivered!`]);
            } else {
                const txt = await res.text();
                setNotifications((n) => [...n.slice(0, -1), `❌ Delivery failed: ${res.status} ${txt}`]);
            }
        } catch (e) {
            setNotifications((n) => [...n.slice(0, -1), `❌ Agent service offline`]);
        }
    };

    const handleSubscribe = () => {
        if (!chatId.trim()) return;
        // Tell the developer agent service about this subscription once at subscribe time
        fetch(`${DEV_SERVICE_URL}/subscribe`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: chatId, chat_id: chatId }),
        }).catch(() => {
            // Non-blocking: allow local demo even if agent service not available
            console.warn("Could not register subscription with dev service");
        });

        setSubscribed(true);
        setShowModal(false);
        setWasInRange(price >= LOW_THRESHOLD && price <= HIGH_THRESHOLD);
        setNotifications([`🎉 Subscribed!`, `📊 Alert when ETH < $3K or > $4K`]);
    };

    return (
        <div className="app">
            <div className="demo-badge">
                <span className="badge-label">DEMO APP</span>
                <span className="badge-text">Built by a developer using our SDK</span>
            </div>

            <header className="header">
                <h1>🐋 Whale Watcher</h1>
                <p>Get notified on price breakouts</p>
            </header>

            <main className="main">
                {!subscribed ? (
                    <div className="hero">
                        <div className="hero-content">
                            <h2>Never Miss a Breakout</h2>
                            <p>Get instant alerts when ETH breaks $3,000 or $4,000</p>

                            <div className="sdk-info-box" onClick={() => setShowSdkInfo(!showSdkInfo)}>
                                <div className="sdk-header">
                                    <span className="sdk-badge">⚡ Powered by x402-Notify SDK</span>
                                    <span className="sdk-toggle">{showSdkInfo ? "▲" : "▼"}</span>
                                </div>
                                {showSdkInfo && (
                                    <div className="sdk-code">
                                        <pre>{`# Install SDK
pip install x402-notify

# 3 lines to send notification
from x402_notify import NotifyClient
client = NotifyClient(wallet_key="0x...")
client.notify(chat_id, "ETH crashed!")`}</pre>
                                        <p className="sdk-note">SDK handles x402 payment on Base Sepolia automatically</p>
                                    </div>
                                )}
                            </div>

                            <button className="subscribe-btn" onClick={() => setShowModal(true)}>
                                Subscribe for Alerts
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="dashboard">
                        <div className="chart-container">
                            <div className="chart-header">
                                <div className="chart-info">
                                    <span className="label">ETH/USD</span>
                                    <span className="thresholds">Alert: &lt;$3K or &gt;$4K</span>
                                </div>
                                <span className={`price ${price < LOW_THRESHOLD ? "down" : price > HIGH_THRESHOLD ? "up" : ""}`}>
                                    ${price.toLocaleString()}
                                </span>
                            </div>
                            <canvas ref={canvasRef} width={600} height={280} className="chart" />
                        </div>

                        <div className="notifications">
                            <div className="notif-header">
                                <h3>📬 Alerts</h3>
                                <span className="sdk-tag">via x402-Notify</span>
                            </div>
                            <div className="log">
                                {notifications.slice(-6).map((n, i) => (
                                    <div key={i} className="log-item">{n}</div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <h3>Subscribe to Alerts</h3>
                        <p>Get notified when ETH breaks key levels.</p>

                        <div className="instructions">
                            <p><strong>Get your Chat ID:</strong></p>
                            <ol>
                                <li>Message <b>@x402aleartbot</b> on Telegram</li>
                                <li>Send <code>/getId</code></li>
                                <li>Copy & paste below</li>
                            </ol>
                        </div>

                        <input
                            type="text"
                            placeholder="Your Telegram Chat ID"
                            value={chatId}
                            onChange={(e) => setChatId(e.target.value)}
                        />

                        <button className="confirm-btn" onClick={handleSubscribe} disabled={!chatId.trim()}>
                            Start Watching
                        </button>
                    </div>
                </div>
            )}

            <footer className="footer">
                <div className="footer-inner">
                    <div className="footer-left">
                        <span className="footer-label">YOUR PRODUCT</span>
                        <span>x402-Notify SDK + Gateway</span>
                    </div>
                    <div className="footer-divider">→</div>
                    <div className="footer-right">
                        <span className="footer-label">THIS DEMO</span>
                        <span>Whale Watcher (uses your SDK)</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
