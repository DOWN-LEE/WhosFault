import requests
import asyncio
from core.redis.Redis import RedisQueue

API_KEY='key'
headers = {'X-Riot-Token':API_KEY}


url_by_name = 'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/'
url_rank_by_summonerid = 'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/'
url_matchlist_by_accontid = 'https://kr.api.riotgames.com/lol/match/v4/matchlists/by-account/'
url_match_by_gameid = 'https://kr.api.riotgames.com/lol/match/v4/matches/'
url_timeline_by_gameid = 'https://kr.api.riotgames.com/lol/match/v4/timelines/by-match/'



def api_summoner(username):
    return requests.get(url_by_name + username, headers=headers)


async def api_rankinfo(summoner_id, dic):
    dic["rankinfo"] = requests.get(url_rank_by_summonerid + summoner_id, headers=headers)

async def api_matchlist(accountId, dic):
    dic["matchlist"] = requests.get(url_matchlist_by_accontid + accountId, headers=headers)

async def api_rank_matchlist(summoner_id, accountId, dic):
    await asyncio.wait([                          
        api_rankinfo(summoner_id, dic),
        api_matchlist(accountId, dic)
    ])






