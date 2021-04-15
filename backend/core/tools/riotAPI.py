import requests
import asyncio
import os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.redis.Redis import RedisQueue
import time

API_KEY='key'
headers = {'X-Riot-Token':API_KEY}
NUMS_BY_ONETIME = 15

url_by_name = 'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/'
url_rank_by_summonerid = 'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/'
url_matchlist_by_accontid = 'https://kr.api.riotgames.com/lol/match/v4/matchlists/by-account/'
url_match_by_gameid = 'https://asia.api.riotgames.com/lol/match/v5/matches/'
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



async def api_matchid(matchid):
    print(requests.get(url_match_by_gameid + matchid, headers=headers))


async def matchlist_async(matchidlist):
    print("start!")
    start = time.time()
    await asyncio.wait([
       map(lambda x : api_matchid(x), [matchid for matchid in matchidlist])
    ])
    jobs = 
  

    print("time!!!:",time.time()-start)

def api_scheduler():
    print('sib')
    rq = RedisQueue("matches")

    if rq.isEmpty():
        return
    
    matchidlist = map(lambda x : x.decode(), rq.getlist(NUMS_BY_ONETIME+1))

    a=[
    "KR_5132960067",
    "KR_5132441355",
    "KR_5131821939",
    "KR_5130937595",
    "KR_5130023121",
    "KR_5129185806",
    "KR_5128895028",
    "KR_5128004723",
    "KR_5127943746",
    "KR_5126900983",
    "KR_5126698441",
    "KR_5126601224",
    "KR_5126337704",
    "KR_5125132362",
    "KR_5124503762"
    ]
    matchidlist1 = [a for _ in range(15)]
    print('sib')
    asyncio.run(matchlist_async(a))
    print('sib')


    



