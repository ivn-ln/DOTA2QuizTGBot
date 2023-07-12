from requests_html import HTMLSession
from bs4 import BeautifulSoup


class DotaBuffTools:
    def __init__(self):
        self.session = HTMLSession()
        self.soup = None

    def get_dota2_item_names(self, url="https://www.dotabuff.com/items"):
        response = self.session.get(url)
        self.soup = BeautifulSoup(response.html.html, 'html.parser')
        item_dict = {}

        tbody = self.soup.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                td = tr.find('td', class_='cell-xlarge')
                if td:
                    a = td.find('a')
                    if a and 'href' in a.attrs:
                        item_name = a['href']
                        item_value = a.text.strip()
                        item_dict[item_name] = item_value

        return item_dict

    def get_match_data(self, hero, game_mode="", lobby="", region=""):
        response = self.session.get("https://www.dotabuff.com/matches")
        self.soup = BeautifulSoup(response.html.html, "html.parser")
        matches = {}

        tbody = self.soup.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                match_data = {}

                match_id = tr.find("td").find("a")
                if match_id and "href" in match_id.attrs:
                    match_id = match_id["href"]
                else:
                    continue

                game_mode_cell = tr.find_all("td")[1]
                mode = game_mode if game_mode else game_mode_cell.text.split("<div")[0].strip()
                lobby = lobby if lobby else game_mode_cell.find("div").text.strip()

                result = tr.find_all("td")[2].find("a").text.strip()
                region = region if region else tr.find_all("td")[2].find("div").text.strip()
                duration = tr.find_all("td")[3].text.strip()

                heroes_radiant = tr.find_all("td")[4].find_all("a")
                heroes_dire = tr.find_all("td")[5].find_all("a")
                radiant_heroes = [hero["href"] for hero in heroes_radiant]
                dire_heroes = [hero["href"] for hero in heroes_dire]

                match_data["hero"] = hero
                match_data["game_mode"] = {"mode": mode, "lobby": lobby}
                match_data["result"] = result
                match_data["region"] = region
                match_data["duration"] = duration
                match_data["teams"] = {"Radiant": radiant_heroes, "Dire": dire_heroes}

                matches[match_id] = match_data

        return matches
