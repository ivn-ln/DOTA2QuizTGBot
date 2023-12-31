from requests_html import HTMLSession
from bs4 import BeautifulSoup
import logging
import cv2 as cv
import numpy as np
import urllib.request


class DotaBuffTools:
    dotabuff_url = 'https://www.dotabuff.com'

    @staticmethod
    def get_dota2_item_data(url="https://www.dotabuff.com/items"):
        dotabuff_url = "https://" + url.split('/')[2]
        session = HTMLSession()
        response = session.get(url)
        soup = BeautifulSoup(response.html.html, 'html.parser')
        item_dict = {}

        tbody = soup.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                td = tr.find('td', class_='cell-xlarge')
                if td:
                    a = td.find('a')
                    if a and 'href' in a.attrs:
                        item_id = a['href']
                        image_url = dotabuff_url + tr.find('td', class_='cell-icon').img['src']
                        image = get_image_from_url(image_url).tolist()
                        item_info = {
                            "name": a.text.strip(),
                            "image_url": image_url,
                            "image": image
                        }
                        item_dict[item_id] = item_info
        logging.log(logging.INFO, "Item base downloaded")
        return item_dict

    @staticmethod
    def get_dota2_hero_data(url="https://www.dotabuff.com/heroes"):
        dotabuff_url = "https://" + url.split('/')[2]
        session = HTMLSession()
        response = session.get(url)
        soup = BeautifulSoup(response.html.html, 'html.parser')
        hero_dict = {}

        hero_grid = soup.find('div', class_='hero-grid')
        if hero_grid:
            for a in hero_grid.find_all('a'):
                if 'href' in a.attrs:
                    hero_id = a['href']
                    tooltip_response = session.get(dotabuff_url + f"{hero_id}/tooltip")
                    soup = BeautifulSoup(tooltip_response.html.html, 'html.parser')
                    image_url = dotabuff_url + soup.a.img['src']
                    main_attribute = soup.find(class_="tooltip-header").find(class_="subheader").text.split(" Hero")[0].strip()
                    image = get_image_from_url(image_url).tolist()
                    hero_info = {
                        "name": a.find(class_="name").text.strip(),
                        "image_url": image_url,
                        "image": image,
                        "main_attribute": main_attribute
                    }
                    hero_dict[hero_id] = hero_info
        logging.log(logging.INFO, "Hero base downloaded")
        return hero_dict

    @staticmethod
    def get_hero_recent_match_data(limit, hero, game_mode="", lobby="", region="", url="https://www.dotabuff.com/matches"):
        session = HTMLSession()
        response = session.get(url, params={"hero":hero, "game_mode":game_mode, "lobby":lobby, "region":region})

        soup = BeautifulSoup(response.html.html, "html.parser")
        matches = {}

        tbody = soup.find("tbody")
        if tbody:
            for tr in zip(range(limit), tbody.find_all("tr")):
                tr = tr[1]
                match_data = {}

                match_id = tr.find("td").find("a")
                if match_id and "href" in match_id.attrs:
                    match_id = match_id["href"]
                else:
                    continue

                game_mode_cell = tr.find_all("td")[1]
                mode = game_mode.title() if game_mode else game_mode_cell.text.strip()
                if lobby:
                    lobby = lobby.title()
                else:
                    if 'Normal Matchmaking' in mode:
                        lobby = 'Normal Matchmaking'
                    elif 'Ranked Matchmaking' in mode:
                        lobby = 'Ranked Matchmaking'
                    elif 'Battle Cup' in mode:
                        lobby = 'Battle Cup'
                    elif 'Unknown' in mode:
                        lobby = 'Unknown'
                    elif 'Bot' in mode:
                        lobby = 'Bot'
                mode = mode.replace('Normal Matchmaking', '')
                mode = mode.replace('Ranked Matchmaking', '')
                mode = mode.replace('Battle Cup', '')
                mode = mode.replace('Unknown', '')
                mode = mode.replace('Bot', '')

                result = tr.find_all("td")[2].find("a").text.strip()
                region = region if region else tr.find_all("td")[2].find("div").text.strip()
                duration = tr.find_all("td")[3].text.strip()

                itembuild_raw = tr.find_all("td")[4].find_all("a")
                itembuild = [item["href"] for item in itembuild_raw]

                heroes_raw = tr.find_all("td")[5].find_all("a")
                radiant_heroes = [hero["href"] for hero in heroes_raw[:5]]
                dire_heroes = [hero["href"] for hero in heroes_raw[5:]]

                match_data["hero"] = "/heroes/" + hero
                match_data["game_mode"] = {"mode": mode, "lobby": lobby}
                match_data["result"] = result
                match_data["region"] = region
                match_data["duration"] = duration
                match_data["itembuild"] = itembuild
                match_data["teams"] = {"Radiant": radiant_heroes, "Dire": dire_heroes}

                matches[match_id] = match_data

        return matches


def get_image_from_url(image_url):
    request = urllib.request.Request(image_url, headers={'User-agent': 'DOTA2 Telegram Quiz Bot'})
    response = urllib.request.urlopen(request)
    arr = np.asarray(bytearray(response.read()), dtype=np.uint8)
    image = cv.imdecode(arr, -1)
    return image