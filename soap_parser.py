import re
import requests
import lxml
from time import sleep
from pprint import pprint
from bs4 import BeautifulSoup
from pysondb import db


class SoapParser:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = 'https://soap4youand.me/'
        self.db = db.getDb('db.json')
        self.session = self._login()

    def _login(self):
        login_url = self.base_url + 'login'
        payload = {
            'login': self.username,
            'password': self.password
        }
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/106.0.0.0 Safari/537.36 '
        }
        session = requests.Session()
        session.post(login_url, headers=headers, data=payload)
        session.get(self.base_url)

        return session

    def get_shows(self):
        all_show_response = self.session.get(self.base_url)
        all_show_soup = BeautifulSoup(all_show_response.text, 'lxml')

        all_shows = all_show_soup.find('ul', id='soap')
        all_show_urls = [self.base_url + url.get('href') for url in
                         all_shows.find_all('a', {'href': re.compile('.*soap.*')})]

        count = 0
        for show_url in all_show_urls:
            show_item = self._get_show_page_info(show_url)
            self._write_to_db(show_item)
            count += 1
            print(f"{count} / {len(all_show_urls)}")

        return self.db

    def _get_show_page_info(self, show_url):
        show_response = self.session.get(show_url)
        show_soup = BeautifulSoup(show_response.text, 'lxml')

        show_info = show_soup.find('div', id='info')

        show_id = show_info.find('div', class_='rating_soap').get('data:sid')
        show_genre = [g.text.strip() for g in show_soup.find_all('a', {'href': re.compile('.*genre.*')})]
        show_year = show_info.find('div', text='год выхода:').find_next_sibling().text.strip()
        if show_soup.find('ul', id='soap').find_all('li'):
            show_img = self.base_url + show_soup.find('ul', id='soap').find_all('li')[-1].find('img').get('original-src')
        else:
            show_img = ''
        show_title = show_info.find('h2').find('span').text.replace('(', '').replace(')', '').strip()
        show_description = show_info.find('p').text.strip()
        show_kinopoisk_ranking = show_info.find('a', {'href': re.compile('.*kinopoisk.*')}).text.split()[0]
        show_kinopoisk_url = show_info.find('a', {'href': re.compile('.*kinopoisk.*')}).get('href')

        all_season_items = show_soup.find('ul', id='soap').find_all('li')

        if all_season_items:
            seasons_data = []
            for season in all_season_items:
                season_number = season.find('div', class_='season').text.strip()
                season_url = self.base_url + season.find('a').get('href')
                season_img = self.base_url + season.find('img', {'src': re.compile('.*covers.*')}).get('src')

                episodes_data = self._get_episodes(season_url)

                seasons_item = {
                    'season': season_number,
                    'season_url': season_url,
                    'season_img': season_img,
                    'episodes': episodes_data
                }
                seasons_data.append(seasons_item)
        else:
            seasons_data = []

        show_item = {
            'soap_id': show_id,
            'url': show_url,
            'img': show_img,
            'title': show_title,
            'description': show_description,
            'year': show_year,
            'genre': show_genre,
            'kinopoisk_ranking': show_kinopoisk_ranking,
            'kinopoisk_url': show_kinopoisk_url,
            'seasons': seasons_data
        }
        return show_item

    def _get_episodes(self, season_url):
        season_response = self.session.get(season_url)
        season_soup = BeautifulSoup(season_response.text, 'lxml')

        episodes_list = season_soup.find('ul', class_='list').find_all(
            'li',
            attrs={
                'data:quality': '1',
                'data:translate': 'rus',
                'data:episode': lambda ep: ep != '--'
            })

        episodes_data = []
        for episode in episodes_list:
            episode_number = episode.find('div', class_='number').text.strip()
            episode_title = episode.find('div', class_='title').find('div', class_='ru').text.strip()
            if not episode_title:
                episode_title = 'Эпизод ' + episode_number
            episode_description = episode.find('div', class_='spoile').find('p', class_='text').text.strip()
            episode_id = episode.find('div', class_='play').get('data:eid')

            episode_item = {
                'episode_id': episode_id,
                'episode_number': episode_number,
                'episode_title': episode_title,
                'episode_description': episode_description
            }
            episodes_data.append(episode_item)
        return episodes_data

    def _write_to_db(self, data):
        if self.db.getBy({"soap_id": data['soap_id']}):
            db_id = self.db.getBy({"soap_id": data['soap_id']})[0]['id']
            self.db.updateById(db_id, data)
            print(f"Updated a show: {data['title']} {data['soap_id']}")
            return True
        else:
            self.db.add(data)
            print(f"Added a new show: {data['title']} {data['soap_id']}")
            return True

    def update_shows(self):
        new_shows_url = 'https://soap4youand.me/new/airdate/'
        update_response = self.session.get(new_shows_url)
        soup_update = BeautifulSoup(update_response.text, 'lxml')
        new_shows = soup_update.find('ul', class_='new')
        new_links = [self.base_url + u.get('href') for u in new_shows.find_all('a', {'href': re.compile('.*soap.*')})]
        urls = list(set(new_links))

        count = 0
        for url in urls:
            show_item = self._get_show_page_info(url)
            self._write_to_db(show_item)
            count += 1
            print(f"{count} / {len(urls)}")
        return self.db
