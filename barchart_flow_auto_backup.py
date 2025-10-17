import os, asyncio, datetime
from playwright.async_api import async_playwright

USERNAME = "haywardsjohnny@gmail.com"
PASSWORD = "Reyansh@18"
URL = "https://www.barchart.com/options/options-flow/stocks?useFilter=1"
OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)

async def download_flow():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=250)
        ctx = await browser.new_context(accept_downloads=True)
        page = await ctx.new_page()

        # 1️⃣ Log in
        await page.goto("https://www.barchart.com/login")
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
	await page.click('button[type="submit"]')
	# ✅ safer: wait until the options page or navbar loads instead of "networkidle"
	try:
		await page.wait_for_selector("header, nav, a[href*='/options']", timeout=60000)
	except:
		print("⚠️ Login took longer than expected, continuing anyway.")
        # 2️⃣ Navigate to Options Flow
        await page.goto(URL)
        await page.wait_for_selector("table")

        # 3️⃣ Click Download
        with page.expect_download() as download_info:
            await page.locator("button:has-text('Download')").click()
        download = await download_info.value

        # 4️⃣ Save CSV
        save_path = os.path.join(OUT_DIR, f"barchart_flow_{ts}.csv")
        await download.save_as(save_path)
        print(f"✅ Saved: {save_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(download_flow())

