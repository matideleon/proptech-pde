"""Prueba si Playwright (navegador real) pasa el muro anti-bot de MercadoLibre."""
import asyncio

from playwright.async_api import async_playwright

URL = "https://listado.mercadolibre.com.uy/inmuebles/alquiler/maldonado/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=UA,
            locale="es-UY",
            viewport={"width": 1366, "height": 900},
        )
        page = await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)

        final_url = page.url
        title = await page.title()
        # Contar fichas de resultado
        count = await page.locator("li.ui-search-layout__item, div.ui-search-result").count()
        price_count = await page.locator(".andes-money-amount__fraction").count()

        print(f"final_url : {final_url[:80]}")
        print(f"title     : {title[:70]}")
        print(f"fichas    : {count}")
        print(f"precios   : {price_count}")
        print(f"bloqueado : {'account-verification' in final_url}")

        if count > 0:
            # Muestra de las primeras 3
            for i in range(min(3, count)):
                item = page.locator("li.ui-search-layout__item, div.ui-search-result").nth(i)
                txt = (await item.inner_text())[:90].replace("\n", " | ")
                print(f"  [{i}] {txt}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
