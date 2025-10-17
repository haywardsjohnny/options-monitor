import os, asyncio, datetime, glob, time
from pathlib import Path
from playwright.async_api import async_playwright

# === CREDENTIALS (as you requested) ===
USERNAME = "haywardsjohnny@gmail.com"
PASSWORD = "Reyansh@18"

# === CONFIGURATION ===
URL = "https://www.barchart.com/options/options-flow/stocks?useFilter=1"
OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)
DEFAULT_DL_DIR = str(Path.home() / "Downloads")  # macOS default download path

async def download_flow():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        ctx = await browser.new_context(accept_downloads=True)
        page = await ctx.new_page()

        # ---- 1️⃣ Log in ----
        print("🔑 Logging in...")
        await page.goto("https://www.barchart.com/login")

        # Accept cookies if needed
        try:
            await page.locator("button:has-text('Accept')").click(timeout=3000)
        except:
            pass

        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await asyncio.sleep(5)
        print("✅ Logged in. Navigating to Options Flow page...")

        # ---- 2️⃣ Navigate straight to Options Flow ----
        await page.goto(URL)
        try:
            await page.locator("button:has-text('Accept')").click(timeout=3000)
        except:
            pass
        await asyncio.sleep(5)
        await page.screenshot(path="after_login.png")
        print("📸 Screenshot saved as after_login.png")

        # ---- 3️⃣ Click the lowercase 'download' button ----
        print("🔎 Searching for 'download' button...")

        selectors = [
            "button:has-text('download')",
            "a:has-text('download')",
            "div:has-text('download')",
            "span:has-text('download')"
        ]

        for sel in selectors:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"➡️ Found element: {sel}")
                target = page.locator(sel).first
                if not await target.is_visible():
                    continue

                # Record baseline CSVs in Downloads folder
                before = set(glob.glob(os.path.join(DEFAULT_DL_DIR, "*.csv")))

                try:
                    async with page.expect_download(timeout=60000) as download_info:
                        await target.click()
                    download = await download_info.value
                    save_path = os.path.join(OUT_DIR, f"barchart_flow_{ts}.csv")
                    await download.save_as(save_path)
                    print(f"✅ Saved CSV via Playwright → {save_path}")
                    break
                except Exception as e:
                    print(f"⚠️ No native download detected ({e}); checking ~/Downloads...")
                    time.sleep(8)
                    after = set(glob.glob(os.path.join(DEFAULT_DL_DIR, "*.csv")))
                    new_files = list(after - before)
                    if new_files:
                        newest = max(new_files, key=os.path.getctime)
                        dest = os.path.join(OUT_DIR, f"barchart_flow_{ts}.csv")
                        os.rename(newest, dest)
                        print(f"✅ Fallback copied {newest} → {dest}")
                        break
                    else:
                        print("❌ No CSV appeared in ~/Downloads.")
        else:
            print("⚠️ No element with text 'download' found on page.")

        await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(download_flow())

