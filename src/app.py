import time
from typing import List, Optional, Dict, Union, Any
import re
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, DataError
from sqlalchemy.orm import Session
from requests import request
from bs4 import BeautifulSoup as bs

from database import engine
from models.model_lot import Lots, Regions, Status, Organizers


def month_to_int(data_str: str) -> str:
    """
    Reformat data
    :param data_str: String with original data
    :return: String in format YYYY-MM-DD
    """
    month = {
        "января": "01",
        "февраля": "02",
        "марта": "03",
        "апреля": "04",
        "мая": "05",
        "июня": "06",
        "июля": "07",
        "августа": "08",
        "сентября": "09",
        "октября": "10",
        "ноября": "11",
        "декабря": "12",
    }
    sep_data = data_str.split(" ")
    sep_data[1] = month[sep_data[1]]
    sep_data.reverse()
    return "-".join(sep_data)


def get_page_content(url: str) -> object:
    """
    Get content from current page
    :param url:
    :return: Beautiful Soup Object
    """
    time.sleep(1)
    resp = request(url=url, method="get", timeout=20)
    if resp.status_code == 200:
        soup = bs(resp.content, "html.parser")
        return soup
    else:
        time.sleep(10)
        get_pages_count(url)


def get_pages_count(url: str) -> int:
    """
    Get count of page
    :param url: Url of first page
    :return: count of page
    """
    soup = get_page_content(url)
    return soup.css.select('a[aria-label="Next"]')[0].get("href").split("?ap=")[1]


def get_link_list(start: int = 1, count: int = 2) -> List:
    """
    Get All link from page, to detail page of element
    :param start: Start page
    :param count: Range of page from first to count
    :return: List of link
    """
    count += 1
    link_list = []
    for number in range(start, count):
        url = f'https://nedradv.ru/nedradv/ru/auction/?ap={number}'
        soup = get_page_content(url)
        link_mass = soup.css.select('td[nowrap]')

        link_list.append([element.a.get("href") for element in link_mass])
    return link_list


def get_data_from_tabel(count: int, link: str, tag_num: int) -> str:
    """
    Return missing data from General page, like Region, Date, Status
    :param count: Number of page with element
    :param link: Link for search html block with element
    :param tag_num: Number of html tag
    :return: String with data from tag
    """
    url = f'https://nedradv.ru/nedradv/ru/auction/?ap={count}'
    print(url, "-----", link)
    soup = get_page_content(url)
    data = soup.find_all(href=link)
    print(data)
    return data[tag_num].text.split("\n")[1]


def get_aucc_data(link: str, count: int) -> Optional[dict[str, Union[str, Any]]]:

    """
    Get data from detail page. Add it to the dict
    :param link: Link detail page
    :param count: Number general page with element
    :return: Dictionary for add to DataBase
    """
    url = f'https://nedradv.ru{link}'
    data_dict = {}

    soup = get_page_content(url)

    header = soup.find_all("h1", class_="card-header")
    if header:
        header_list = header[0].text.split("\n")
        date_new = month_to_int(header_list[1])
        data_dict["date"] = date_new
        data_dict["place"] = header_list[2]

    else:
        time.sleep(5)
        get_aucc_data(link, count)
        return None

    region = soup.find("p", class_="card-header")
    neg_status_list = ["Закрыт", "Отмена", "Аннулирован", "Перенос", "Приостановлен"]

    if region is not None:
        reg = region.text.split("\n")[1].split(",")
        if len(reg) < 3:
            data_dict["region"] = reg[0]
            data_dict["district"] = ""
        else:
            data_dict["region"] = reg[0]
            data_dict["district"] = reg[1]
    else:
        data_dict["region"] = get_data_from_tabel(count, link, tag_num=2)
        data_dict["district"] = ""

    row_data = soup.find_all("dl", class_="row")
    if len(row_data) > 5:
        data_dict["status"] = row_data[0].dd.text
        if data_dict["status"] not in neg_status_list:
            print(data_dict["status"])
            data_dict["deadline"] = row_data[7].dd.text
        else:
            data_dict["deadline"] = ""
        deposit_int = re.findall(r'\d+', row_data[3].dd.text.split("(")[0])
        data_dict["deposit"] = int("".join(deposit_int))
        data_dict["organizer"] = row_data[5].dd.text
    else:
        data_dict["status"] = get_data_from_tabel(count, link, tag_num=3).split(",")[0]
        data_dict["deadline"] = ""
        deposit_int = re.findall(r'\d+', row_data[2].dd.text.split("(")[0])
        data_dict["deposit"] = int("".join(deposit_int))
        data_dict["organizer"] = row_data[4].dd.text

    print(data_dict)
    return data_dict


def check_entry(session: Session, check_data: str, table_model, col_name) -> Optional[int]:
    """
    Check entry in DB. If exist return id of entry.
    :param session: DB session
    :param check_data: data
    :param table_model: Tabel Name
    :param col_name: Column name
    :return: Id or None
    """
    try:
        stmt = select(table_model).where(col_name == check_data)
        resp = session.scalars(stmt).one()
        return resp.id
    except NoResultFound:
        return None


def add_to_db(data: Dict):
    """
    Add data to DB from Dict with data
    :param data: Dict with data to add
    :return:
    """
    with Session(engine) as session:
        new_row = Lots(
            place=data["place"],
            date_add=data["date"],
            deadline=data["deadline"],
            deposit=data["deposit"]
        )
        id_region = check_entry(session, data["region"], Regions, Regions.region_name)
        if not id_region:
            new_row.regions = Regions(region_name=data["region"])
        else:
            new_row.region = id_region

        id_organizer = check_entry(session, data["organizer"], Organizers, Organizers.org_name)
        if not id_organizer:
            new_row.organizers = Organizers(org_name=data["organizer"])
        else:
            new_row.organizer = id_organizer

        id_status = check_entry(session, data["status"], Status, Status.status)
        if not id_status:
            new_row.statuses = Status(status=data["status"])
        else:
            new_row.status = id_status
        try:
            session.add(new_row)
            session.commit()
        except DataError:
            print(DataError)


def main():
    url = f'https://nedradv.ru/nedradv/ru/auction'
    count = get_pages_count(url)
    start = 1
    all_link = get_link_list(start, count=2)  # TODO Change param of function to count variable for get All pages
    print(all_link)

    count = start
    for list_link in all_link:
        for link in list_link:
            data_dict = get_aucc_data(link, count)
            add_to_db(data_dict)
        count += 1


if __name__ == "__main__":
    main()
