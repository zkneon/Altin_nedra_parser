"""
Это была пробная версия, хотел выполнить асинхронно.
Но сайт не выдерживает, и начинает отдавать (500) ответы.
"""

import platform
import time
from typing import List, Dict
from bs4 import BeautifulSoup as bs

import aiohttp
import asyncio


async def get_link(session, url) -> List:
    async with session.get(url) as resp:
        content = await resp.text()
        soup = bs(content, "html.parser")
        link_mass = soup.css.select('td[nowrap]')

        return [element.a.get("href") for element in link_mass]


async def get_pages_count(session, url) -> str:
    resp = await session.get(url)
    content = await resp.text()
    soup = bs(content, "html.parser")
    return soup.css.select('a[aria-label="Next"]')[0].get("href").split("?ap=")[1]


async def get_data_from_tabel(session, count, link, tag_num):
    url = f'https://nedradv.ru/nedradv/ru/auction/?ap={count}'
    print(url, "-----", link)
    resp = await session.get(url)
    content = await resp.text()
    soup1 = bs(content, "html.parser")
    data = soup1.find_all(href=link)
    return data[tag_num].text


async def get_aucc_data(session, link, count) -> None:
    url = f'https://nedradv.ru{link}'
    data_dict = {}

    async with session.get(url) as resp:
        print(resp.status)
        if resp.status == 200:
            content = await resp.text()
            soup = bs(content, "html.parser")
            header = soup.find_all("h1", class_="card-header")
            if header:
                header_list = header[0].text.split("\n")
                data_dict["date"] = header_list[1]
                data_dict["place"] = header_list[2]
            else:
                data_dict["place"] = await get_data_from_tabel(session, count, link, tag_num=1)

            region = soup.find("p", class_="card-header")
            if region is not None:

                region = region.text.split("\n")[1].split(",")
                if len(region) < 3:
                    data_dict["region"] = region[0]
                    data_dict["district"] = ""
                else:
                    data_dict["region"] = region[0]
                    data_dict["district"] = region[1]
            else:
                data_dict["region"] = await get_data_from_tabel(session, count, link, tag_num=2)
                data_dict["district"] = ""
            print(data_dict)
        else:
            time.sleep(30)
            await get_aucc_data(session, link, count)


async def main():
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20, connect=20, )) as session:
        url = f'https://nedradv.ru/nedradv/ru/auction'
        count = await get_pages_count(session, url)
        print(int(count))
        tasks = []
        for number in range(1, 3):
            url = f'https://nedradv.ru/nedradv/ru/auction/?ap={number}'
            tasks.append(asyncio.ensure_future(get_link(session, url)))

        original = await asyncio.gather(*tasks,)

        tasks = []
        count = 1
        for link_list in original:
            for link in link_list:
                tasks.append(asyncio.ensure_future(get_aucc_data(session, link, count)))
            count += 1
            print(tasks)
            await asyncio.gather(*tasks)
            time.sleep(30)

if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
