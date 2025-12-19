import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { ethers } from "ethers";
import TelegramBot from "node-telegram-bot-api";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Configuration
const GATEWAY_WALLET = process.env.GATEWAY_WALLET_ADDRESS || "0x1234567890123456789012345678901234567890";
const MESSAGE_PRICE_ETH = process.env.MESSAGE_PRICE_ETH || "0.00001";
const RPC_URL = process.env.RPC_URL || "https://sepolia.base.org";
const EXPECTED_CHAIN_ID = parseInt(process.env.CHAIN_ID || "84532", 10);
const MIN_CONFIRMATIONS = parseInt(process.env.MIN_CONFIRMATIONS || "1", 10);
const DEMO_TX_PREFIX = process.env.DEMO_TX_PREFIX || "0x_DEMO_TX_";
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

const provider = new ethers.providers.JsonRpcProvider(RPC_URL);
// Processed transactions store (simple file-backed cache for idempotency)
import Redis from "ioredis";
const REDIS_URL = process.env.REDIS_URL || null;
const REDIS_CONNECT_RETRIES = parseInt(process.env.REDIS_CONNECT_RETRIES || "5", 10);
const REDIS_CONNECT_DELAY_MS = parseInt(process.env.REDIS_CONNECT_DELAY_MS || "2000", 10);
let redisClient: Redis | null = null;

if (REDIS_URL) {
    redisClient = new Redis(REDIS_URL);
    redisClient.on("error", (err) => console.warn("Redis error:", err));
}

// ============================================
// TELEGRAM BOT SETUP
// ============================================
let bot: TelegramBot | null = null;

if (TELEGRAM_BOT_TOKEN) {
    bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });
    console.log("📱 Telegram bot connected!");

    // /start command
    bot.onText(/\/start/, (msg) => {
        const chatId = msg.chat.id;
        bot?.sendMessage(
            chatId,
            `👋 Welcome to <b>x402-Notify</b>!\n\n` +
            `This bot delivers notifications from AI agents.\n\n` +
            `🔑 <b>Your Chat ID:</b>\n<code>${chatId}</code>\n\n` +
            `📋 Copy this ID and paste it into services like Whale Watcher to receive alerts!`,
            { parse_mode: "HTML" }
        );
    });

    // /getId command
    bot.onText(/\/getId/, (msg) => {
        const chatId = msg.chat.id;
        bot?.sendMessage(
            chatId,
            `🔑 <b>Your Chat ID:</b>\n<code>${chatId}</code>\n\n` +
            `📋 Tap to copy, then paste into any x402-Notify service!`,
            { parse_mode: "HTML" }
        );
    });

    // Any other message
    bot.on("message", (msg) => {
        if (msg.text?.startsWith("/")) return; // Skip commands
        const chatId = msg.chat.id;
        bot?.sendMessage(
            chatId,
            `Your Chat ID is: <code>${chatId}</code>\n\n` +
            `Use /start for more info.`,
            { parse_mode: "HTML" }
        );
    });
} else {
    console.log("⚠️ No TELEGRAM_BOT_TOKEN - bot commands disabled");
}

// ============================================
// SEND TELEGRAM MESSAGE (for notifications)
// ============================================
async function sendTelegram(chatId: string, message: string): Promise<boolean> {
    if (!bot) {
        console.log(`[MOCK TELEGRAM] To ${chatId}: ${message}`);
        return true;
    }

    try {
        await bot.sendMessage(chatId, message, { parse_mode: "HTML" });
        return true;
    } catch (e: any) {
        console.error("Telegram error:", e.message);
        return false;
    }
}

// ============================================
// x402 NOTIFY ENDPOINT
// ============================================
app.post("/notify", async (req, res) => {
    const { chat_id, message } = req.body;
    // Accept either `x-payment-tx` (classic) or `x-agent-payment-tx` (explicit agent-paid flow)
    const paymentTxHash = (req.headers["x-payment-tx"] || req.headers["x-agent-payment-tx"]) as string;

    if (!chat_id || !message) {
        return res.status(400).json({ error: "Missing chat_id or message" });
    }

    // No payment? Return 402 with x402 instructions
    if (!paymentTxHash) {
        return res.status(402).json({
            error: "Payment Required",
            x402: {
                version: "1.0",
                accepts: [{
                    scheme: "exact",
                    network: "base-sepolia",
                    maxAmountRequired: MESSAGE_PRICE_ETH,
                    payTo: GATEWAY_WALLET,
                    asset: "ETH",
                }],
            },
        });
    }
    // Demo txs (used by the demo app) - accept them locally without on-chain verification
    if (paymentTxHash.startsWith(DEMO_TX_PREFIX)) {
        console.log("Received demo payment header, accepting for demo mode", paymentTxHash);
        const sent = await sendTelegram(chat_id, message);
        if (!sent) return res.status(500).json({ error: "Telegram delivery failed (demo)" });
        return res.json({ success: true, txHash: paymentTxHash, demo: true });
    }

    // Verify payment on-chain
    try {
        // Check network chain id
        const network = await provider.getNetwork();
        if (network.chainId !== EXPECTED_CHAIN_ID) {
            console.warn(`Provider chainId ${network.chainId} does not match expected ${EXPECTED_CHAIN_ID}`);
        }

        const tx = await provider.getTransaction(paymentTxHash);
        if (!tx) {
            return res.status(402).json({ error: "Transaction not found on network" });
        }

        // Recipient check
        if (tx.to?.toLowerCase() !== GATEWAY_WALLET.toLowerCase()) {
            return res.status(402).json({ error: "Invalid recipient (did not pay Gateway)" });
        }

        // Amount check
        const required = ethers.utils.parseEther(MESSAGE_PRICE_ETH);
        if (tx.value.lt(required)) {
            const valueInEth = ethers.utils.formatEther(tx.value);
            return res.status(402).json({ error: `Insufficient payment. Sent ${valueInEth}, required ${MESSAGE_PRICE_ETH}` });
        }

        // Wait for receipt to ensure it's mined and successful
        const receipt = await provider.getTransactionReceipt(paymentTxHash);
        if (!receipt || !receipt.blockNumber) {
            return res.status(402).json({ error: "Transaction not yet mined" });
        }

        if (receipt.status !== 1) {
            return res.status(402).json({ error: "Payment transaction failed on-chain" });
        }

        // Optional confirmations check
        if (MIN_CONFIRMATIONS > 0) {
            const current = await provider.getBlockNumber();
            const confirmations = current - receipt.blockNumber + 1;
            if (confirmations < MIN_CONFIRMATIONS) {
                return res.status(402).json({ error: `Waiting for confirmations. Have ${confirmations}, need ${MIN_CONFIRMATIONS}` });
            }
        }

        // Idempotency: if we've already processed this tx, return success
        try {
            if (redisClient) {
                const exists = await redisClient.get(`processed:${paymentTxHash}`);
                if (exists) return res.json({ success: true, txHash: paymentTxHash, idempotent: true });
            }
        } catch (e) {
            console.warn("Redis idempotency check failed:", e);
        }

        // Deliver message
        const sent = await sendTelegram(chat_id, message);
        if (!sent) return res.status(500).json({ error: "Telegram delivery failed" });

        // Mark processed in Redis (with TTL)
        try {
            if (redisClient) {
                await redisClient.set(`processed:${paymentTxHash}`, "1", "EX", 60 * 60 * 24 * 7); // 7 days
            }
        } catch (e) {
            console.warn("Redis mark-processed failed:", e);
        }

        return res.json({ success: true, txHash: paymentTxHash });
    } catch (e: any) {
        console.error("Error verifying payment:", e);
        return res.status(500).json({ error: e.message });
    }
});

// Health check
app.get("/", (req, res) => {
    res.json({
        service: "x402-Notify Gateway",
        bot: bot ? "@x402aleartbot" : "disabled",
        pricing: { perMessage: MESSAGE_PRICE_ETH + " ETH" },
        network: { rpc: RPC_URL, expectedChainId: EXPECTED_CHAIN_ID, minConfirmations: MIN_CONFIRMATIONS },
    });
});

async function startServer() {
    // If Redis is configured, verify connectivity before starting
    if (redisClient) {
        let attempt = 0;
        let connected = false;
        while (attempt < REDIS_CONNECT_RETRIES) {
            try {
                const pong = await redisClient.ping();
                if (pong === "PONG" || pong === "OK") {
                    connected = true;
                    break;
                } else {
                    console.warn(`Redis ping returned unexpected response: ${pong}`);
                }
            } catch (e: any) {
                console.warn(`Redis ping attempt ${attempt + 1} failed:`, e.message || e);
            }

            attempt += 1;
            if (attempt < REDIS_CONNECT_RETRIES) {
                console.log(`Retrying Redis connection in ${REDIS_CONNECT_DELAY_MS}ms... (attempt ${attempt + 1}/${REDIS_CONNECT_RETRIES})`);
                await new Promise((r) => setTimeout(r, REDIS_CONNECT_DELAY_MS));
            }
        }

        if (!connected) {
            console.error(`❌ Unable to connect to Redis at REDIS_URL after ${REDIS_CONNECT_RETRIES} attempts`);
            process.exit(1);
        }

        console.log("✅ Connected to Redis for idempotency");
    }

    app.listen(PORT, () => {
        console.log(`
    ╔═══════════════════════════════════════════╗
    ║     x402-Notify Gateway                   ║
    ║     http://localhost:${PORT}                  ║
    ╠═══════════════════════════════════════════╣
    ║  Bot: ${bot ? "✅ Active" : "❌ No token"}                         ║
    ║  Network RPC: ${RPC_URL}                    ║
    ║  Expected Chain ID: ${EXPECTED_CHAIN_ID} (Base Sepolia) ║
    ║  POST /notify - Send notification         ║
    ╚══════════════════════════════════════════╝
    `);
    });
}

startServer();
