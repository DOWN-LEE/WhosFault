import requests
import asyncio
import os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.redis.Redis import RedisQueue
import time
import aiohttp

API_KEY='key~'
headers = {'X-Riot-Token':API_KEY}
NUMS_BY_ONETIME = 15

url_by_name = 'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/'
url_rank_by_summonerid = 'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/'
url_matchlist_by_puuid = 'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{}?start={}&end={}'

url_timeline_by_gameid = 'https://asia.api.riotgames.com/lol/match/v5/matches/{}/timeline'
url_match_by_gameid = 'https://asia.api.riotgames.com/lol/match/v5/matches/{}'


def api_summoner(username):
    return requests.get(url_by_name + username, headers=headers)


def api_rankinfo(summoner_id):
    return requests.get(url_rank_by_summonerid + summoner_id, headers=headers)

def api_matchlist(puuid):
    return requests.get(url_matchlist_by_puuid.format(puuid, '0', '100'), headers=headers)



def analyze_match(matchinfo):
    return 1

async def api_match_matchid(session, rq, matchid):
    async with session.get(url_match_by_gameid.format(matchid), headers=headers) as resp:
        matchinfo = await resp.json()
        result = analyze_match(matchinfo)
        ### result를 rq에 key=matchid로 집어넣기
        

async def api_timeline_matchid(session, matchid):
    async with session.get(url_timeline_by_gameid.format(matchid), headers=headers) as resp:
        pokemon = await resp.json()



async def matchlist_async(matchidlist, rq):
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for matchid in matchidlist:
            tasks.append(asyncio.ensure_future(api_match_matchid(session, rq, matchid)))
            #tasks.append(asyncio.ensure_future(api_timeline_matchid(session, matchid)))

        await asyncio.gather(*tasks)


def api_scheduler():
    rq = RedisQueue("matches")

    if rq.isEmpty():
        return

    matchidlist = map(lambda x : x.decode(), rq.getlist(NUMS_BY_ONETIME+1))

    asyncio.run(matchlist_async(matchidlist, rq))



# asyncio.run(matchlist_async(["KR_5161780417"
#     ]))
