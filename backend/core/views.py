import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
######
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render
from core.models import Summoner
from core.tools.tools import *
from core.tools.riotAPI import *
from core.redis.Redis import RedisQueue

import requests
import json
import time
import asyncio


MATCHES_NUM = 8

queue_table = {'420':'solo', '430':'normal', '440':'flex', '450':'aram', '900':'URF'}
queue_target = [420,430,440]

def get_result(request, username='원스타교장샘'):
    start = time.time()
    try:
        Summoner.objects.get(name=username)
    except: #소환사가 db에 없엉 ㅠㅠ
        pass

    summoner = requests.get(url_by_name + username, headers=headers)

    if summoner.status_code != 200:
        print('wrong 잘못된 소환사 이름')
    
    summoner = json.loads(summoner.text)
    summonerLevel = summoner['summonerLevel']
    profileIconId = summoner['profileIconId']
    summoner_id = summoner['id']
    accountId = summoner['accountId']
    puuid = summoner['puuid']

    rankinfo = requests.get(url_rank_by_summonerid + summoner_id, headers=headers)

    if rankinfo.status_code != 200:
        print('wrong')

    solo_rank = { 'rank':0, 'wins':0, 'losses':0 }
    flex_rank = { 'rank':0, 'wins':0, 'losses':0 }
    rankinfo = json.loads(rankinfo.text)
    for rank in rankinfo:
        target_rank=None
        if rank['queueType'] == 'RANKED_FLEX_SR':
            target_rank=flex_rank
        elif rank['queueType'] == 'RANKED_SOLO_5x5':
            target_rank=solo_rank
        else:
            continue

        target_rank['rank'] = rankToNum(rank['tier'], rank['rank'])
        target_rank['wins'] = rank['wins']
        target_rank['losses'] = rank['losses']
    
    target_summoner = Summoner(
        name = username,
        summonerId = summoner_id,
        accountId = accountId,
        puuid = puuid,
        profileIconId = int(profileIconId),
        summonerLevel = int(summonerLevel),
        solo_rank = solo_rank['rank'],
        solo_rank_win = solo_rank['wins'],
        solo_rank_loss = solo_rank['losses'],
        flex_rank = flex_rank['rank'],
        flex_rank_win = flex_rank['wins'],
        flex_rank_loss = flex_rank['losses']
    )


    matchlist = requests.get(url_matchlist_by_accontid + accountId, headers=headers)
    if matchlist.status_code != 200:
        print('wrong')
    
    matchlist = json.loads(matchlist.text)['matches']
    real_matchlist=[]
    for m in matchlist:
        if m['queue'] in queue_target:
            real_matchlist.append(m)
        if len(real_matchlist) >= 8:
            break

    matches=[]
    average=0
    for match in real_matchlist:
        data = {}
        match_id = str(match['gameId'])
        player_champ = match['champion']
        # if match['queue'] not in queue_target:
        #     data['fault'] = False
        # else:
        #     data['fault'] = True
        
        matchinfo = requests.get(url_match_by_gameid + match_id, headers=headers)
        if matchinfo.status_code != 200:
            print('wrong')

        matchtimeline = requests. get(url_timeline_by_gameid + match_id, headers=headers)
        if matchtimeline.status_code != 200:
            print('wrong')

        matchinfo = json.loads(matchinfo.text)
        matchtimeline = json.loads(matchtimeline.text)
        
        try:
            lane = roleml.predict(matchinfo, matchtimeline)
        except:
            print(match)
            return HttpResponse(status=400)
        position = laneToPos(lane)

        pos_to_score, team1_shit, team2_shit = calScore(matchinfo, matchtimeline['frames'], position)

        players={}
        players_champ={}
        player_id=1
        for p in matchinfo["participantIdentities"]:
            players[position[p['participantId']]] = p['player']['summonerName']
            if str(p['player']['summonerName']).strip().lower()== username.strip().lower():
                player_id = p['participantId']
        for p in matchinfo['participants']:
            players_champ[position[p['participantId']]] = p['championId']
            if player_champ == p['championId']:
                player_spell1 = p['spell1Id']
                player_spell2 = p['spell2Id']
                player_win = p['stats']['win']
                player_kills = p['stats']['kills']
                player_deaths = p['stats']['deaths']
                player_assists = p['stats']['assists']

        data['champion'] = player_champ
        data['spell1'] = player_spell1
        data['spell2'] = player_spell2
        data['win'] = player_win
        data['gameType'] = match['queue']
        data['kill'] = player_kills
        data['death'] = player_deaths
        data['assist'] = player_assists
        data['win_team'] = 100 if matchinfo["teams"][0]['win'] =='Win' else 200
        data['team1_shit']= team1_shit
        data['team2_shit'] = team2_shit
        data['players'] = players
        data['players_champ'] = players_champ
        matches.append(data)
        average += pos_to_score[position[player_id]]
    
    
    response_dict = {
        'user_name': username,
        'user_level': summonerLevel,
        'user_profile' : profileIconId,
        'solo_rank' : solo_rank,
        'flex_rank' : flex_rank,
        'matches' : matches,
        'average' : average
    }
    print("time :", time.time() - start)
    return HttpResponse(content=json.dumps(response_dict), status=203)
    
    

def get_userinfo(request, username='원스타교장샘'):
    if request.method == 'GET':
        try:
            summoner = Summoner.objects.get(name=username)

            response_dict = {
            'user_name': summoner.name,
            'user_level': summoner.summonerLevel,
            'user_profile' : summoner.profileIconId,
            'solo_rank' : {'rank':summoner.solo_rank, 'wins':summoner.solo_rank_win, 'losses':summoner.solo_rank_loss},
            'flex_rank' : {'rank':summoner.flex_rank, 'wins':summoner.flex_rank_win, 'losses':summoner.flex_rank_loss},
            }

            return HttpResponse(content=json.dumps(response_dict), status=203)

        except:
            pass

        summoner = api_summoner(username=username)
        if summoner.status_code != 200:
            # 없는 소환사
            return HttpResponse(status=404)

        summoner = json.loads(summoner.text)
        summonerLevel = summoner['summonerLevel']
        profileIconId = summoner['profileIconId']
        summoner_id = summoner['id']
        accountId = summoner['accountId']
        puuid = summoner['puuid']

        rankinfo = api_rankinfo(summoner_id=summoner_id)

        if rankinfo.status_code != 200:
            return HttpResponse(status=400)

        solo_rank = { 'rank':0, 'wins':0, 'losses':0 }
        flex_rank = { 'rank':0, 'wins':0, 'losses':0 }
        rankinfo = json.loads(rankinfo.text)
        for rank in rankinfo:
            target_rank=None
            if rank['queueType'] == 'RANKED_FLEX_SR':
                target_rank=flex_rank
            elif rank['queueType'] == 'RANKED_SOLO_5x5':
                target_rank=solo_rank
            else:
                continue

            target_rank['rank'] = rankToNum(rank['tier'], rank['rank'])
            target_rank['wins'] = rank['wins']
            target_rank['losses'] = rank['losses']
        
        target_summoner = Summoner(
            name = username,
            summonerId = summoner_id,
            accountId = accountId,
            puuid = puuid,
            profileIconId = int(profileIconId),
            summonerLevel = int(summonerLevel),
            solo_rank = solo_rank['rank'],
            solo_rank_win = solo_rank['wins'],
            solo_rank_loss = solo_rank['losses'],
            flex_rank = flex_rank['rank'],
            flex_rank_win = flex_rank['wins'],
            flex_rank_loss = flex_rank['losses']
        )

        target_summoner.save()
        response_dict = {
            'user_name': username,
            'user_level': summonerLevel,
            'user_profile' : profileIconId,
            'solo_rank' : solo_rank,
            'flex_rank' : flex_rank,
        }
        return HttpResponse(content=json.dumps(response_dict), status=203)


    
    return HttpResponseNotAllowed(['GET'])



def get_matchinfo(request, username='원스타교장샘'):
    if request.method == 'GET':
        summoner = None
        try:
            summoner = Summoner.objects.get(name=username) 
        except: #소환사가 db에 없엉 ㅠㅠ
            return HttpResponse(status=400)
        
        # Match 가 1개 이상이면 여기서 리턴
        # 아래는 없는 경우
    

        matchlist = api_matchlist(summoner.puuid)

        if matchlist.status_code != 200:
            return HttpResponse(status=400)

        matchlist = json.loads(matchlist.text)
        
        

        rq = RedisQueue("matches")
        for match_id in matchlist:
            rq.push(match_id)
        
        matches_result=[]
        for match_id in matchlist:
            while rq.exist_by_key(match_id)==0:
                time.sleep(0.2)
            
            matches_result.append(rq.get_by_key(match_id))
            rq.del_by_key(match_id)
        
       
        
        return HttpResponse(content=json.dumps(matches_result), status=203)


    return HttpResponseNotAllowed(['GET'])


def get_info_from_db(summoner):
    pass



{ 
'champion':'Lux', 'spell1':'4', 'spell2':'5', 'win':True, 'gameType':'solo',
'kill':10, 'death':4, 'assist':5, 'bus':'Antifasicst', 'cause':'beomsu',
'team1_1_champ':'garen', 'team1_1_name':'시발맨',
}
get_result(1)

a={
    "frames": [
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 554,
                        "y": 581
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 557,
                        "y": 345
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 335,
                        "y": 269
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 194,
                        "y": 457
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 329,
                        "y": 650
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 14180,
                        "y": 14271
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 14176,
                        "y": 14506
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 14398,
                        "y": 14582
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 14539,
                        "y": 14394
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 14404,
                        "y": 14201
                    },
                    "currentGold": 500,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [],
            "timestamp": 0
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 1097,
                        "y": 10020
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 7336,
                        "y": 3434
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6333,
                        "y": 6737
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 7860,
                        "y": 5196
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 4790,
                        "y": 1592
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 4064,
                        "y": 13683
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 11022,
                        "y": 6408
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7122,
                        "y": 9833
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 9711,
                        "y": 4465
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 10291,
                        "y": 4642
                    },
                    "currentGold": 0,
                    "totalGold": 500,
                    "level": 1,
                    "xp": 0,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2898,
                    "participantId": 4,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 3723,
                    "participantId": 8,
                    "itemId": 1055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 4351,
                    "participantId": 8,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 6299,
                    "participantId": 2,
                    "itemId": 1055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 6764,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 6764,
                    "participantId": 1,
                    "itemId": 2033
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 7061,
                    "participantId": 2,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 10363,
                    "participantId": 10,
                    "itemId": 1035
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 10561,
                    "participantId": 1,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 10859,
                    "participantId": 7,
                    "itemId": 3850
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 10925,
                    "participantId": 10,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 11288,
                    "participantId": 10,
                    "itemId": 2031
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 11453,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 11717,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 12279,
                    "participantId": 7,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 14723,
                    "participantId": 4,
                    "itemId": 1035
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 15318,
                    "participantId": 4,
                    "itemId": 2031
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 18026,
                    "participantId": 2,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 21527,
                    "participantId": 5,
                    "itemId": 1055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 22320,
                    "participantId": 5,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 22749,
                    "participantId": 5,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 26085,
                    "participantId": 6,
                    "itemId": 1056
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 26679,
                    "participantId": 6,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 26877,
                    "participantId": 6,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 43496,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 44123,
                    "participantId": 9,
                    "itemId": 2031
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 44652,
                    "participantId": 9,
                    "itemId": 3340
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 49771,
                    "participantId": 9,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 52215,
                    "participantId": 3,
                    "itemId": 3862
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 52314,
                    "participantId": 8,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 52579,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 52745,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 52943,
                    "participantId": 3,
                    "itemId": 3340
                }
            ],
            "timestamp": 60011
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 2177,
                        "y": 12636
                    },
                    "currentGold": 98,
                    "totalGold": 598,
                    "level": 1,
                    "xp": 211,
                    "minionsKilled": 4,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 6824,
                        "y": 5608
                    },
                    "currentGold": 156,
                    "totalGold": 656,
                    "level": 2,
                    "xp": 415,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 6,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6928,
                        "y": 7380
                    },
                    "currentGold": 98,
                    "totalGold": 598,
                    "level": 1,
                    "xp": 240,
                    "minionsKilled": 4,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 12594,
                        "y": 2710
                    },
                    "currentGold": 63,
                    "totalGold": 563,
                    "level": 1,
                    "xp": 113,
                    "minionsKilled": 2,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 12997,
                        "y": 2259
                    },
                    "currentGold": 83,
                    "totalGold": 583,
                    "level": 1,
                    "xp": 113,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 2788,
                        "y": 12820
                    },
                    "currentGold": 42,
                    "totalGold": 542,
                    "level": 1,
                    "xp": 120,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 12155,
                        "y": 6829
                    },
                    "currentGold": 206,
                    "totalGold": 706,
                    "level": 2,
                    "xp": 505,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7739,
                        "y": 7451
                    },
                    "currentGold": 77,
                    "totalGold": 577,
                    "level": 1,
                    "xp": 211,
                    "minionsKilled": 3,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13137,
                        "y": 3556
                    },
                    "currentGold": 84,
                    "totalGold": 584,
                    "level": 1,
                    "xp": 113,
                    "minionsKilled": 3,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13746,
                        "y": 3273
                    },
                    "currentGold": 63,
                    "totalGold": 563,
                    "level": 1,
                    "xp": 113,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 62624,
                    "participantId": 7,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 69989,
                    "participantId": 3,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 76165,
                    "participantId": 10,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 86374,
                    "participantId": 1,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 103516,
                    "participantId": 10,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 104474,
                    "participantId": 6,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 106059,
                    "participantId": 4,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 108867,
                    "participantId": 5,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 116828,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 3
                }
            ],
            "timestamp": 120033
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 2238,
                        "y": 12527
                    },
                    "currentGold": 696,
                    "totalGold": 1196,
                    "level": 2,
                    "xp": 583,
                    "minionsKilled": 7,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 2350,
                        "y": 8378
                    },
                    "currentGold": 503,
                    "totalGold": 1003,
                    "level": 3,
                    "xp": 790,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7393,
                        "y": 7395
                    },
                    "currentGold": 410,
                    "totalGold": 920,
                    "level": 3,
                    "xp": 904,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 13007,
                        "y": 3298
                    },
                    "currentGold": 413,
                    "totalGold": 913,
                    "level": 2,
                    "xp": 564,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13402,
                        "y": 3334
                    },
                    "currentGold": 377,
                    "totalGold": 877,
                    "level": 2,
                    "xp": 564,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 2863,
                        "y": 13006
                    },
                    "currentGold": 297,
                    "totalGold": 797,
                    "level": 3,
                    "xp": 721,
                    "minionsKilled": 9,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 5023,
                        "y": 11493
                    },
                    "currentGold": 488,
                    "totalGold": 988,
                    "level": 3,
                    "xp": 805,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8177,
                        "y": 8230
                    },
                    "currentGold": 381,
                    "totalGold": 881,
                    "level": 3,
                    "xp": 752,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13954,
                        "y": 3985
                    },
                    "currentGold": 346,
                    "totalGold": 846,
                    "level": 2,
                    "xp": 450,
                    "minionsKilled": 11,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13694,
                        "y": 4327
                    },
                    "currentGold": 297,
                    "totalGold": 797,
                    "level": 2,
                    "xp": 450,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 124393,
                    "participantId": 5,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 127960,
                    "participantId": 1,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 129644,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 130073,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 133113,
                    "participantId": 6,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 135327,
                    "participantId": 5,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 135690,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 142465,
                    "participantId": 7,
                    "itemId": 2010
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 144517,
                    "participantId": 3,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 144814,
                    "position": {
                        "x": 3069,
                        "y": 13059
                    },
                    "killerId": 5,
                    "victimId": 9,
                    "assistingParticipantIds": []
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 145342,
                    "participantId": 2,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 146169,
                    "participantId": 10,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 150332,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 153473,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 157040,
                    "participantId": 8,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 157073,
                    "participantId": 7,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 158000,
                    "participantId": 9,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 160180,
                    "participantId": 1,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 167348,
                    "participantId": 6,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 171709,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 172635,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 5
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 174550,
                    "participantId": 9,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 178780,
                    "participantId": 4,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 180035
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 1578,
                        "y": 11688
                    },
                    "currentGold": 1183,
                    "totalGold": 1683,
                    "level": 4,
                    "xp": 1553,
                    "minionsKilled": 11,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 5190,
                        "y": 8639
                    },
                    "currentGold": 711,
                    "totalGold": 1211,
                    "level": 3,
                    "xp": 975,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6820,
                        "y": 7450
                    },
                    "currentGold": 616,
                    "totalGold": 1126,
                    "level": 4,
                    "xp": 1265,
                    "minionsKilled": 17,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 12937,
                        "y": 3340
                    },
                    "currentGold": 725,
                    "totalGold": 1225,
                    "level": 3,
                    "xp": 901,
                    "minionsKilled": 24,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13286,
                        "y": 3292
                    },
                    "currentGold": 640,
                    "totalGold": 1140,
                    "level": 3,
                    "xp": 901,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 10061,
                        "y": 13854
                    },
                    "currentGold": 143,
                    "totalGold": 1043,
                    "level": 3,
                    "xp": 1115,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 4077,
                        "y": 11293
                    },
                    "currentGold": 688,
                    "totalGold": 1188,
                    "level": 3,
                    "xp": 991,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7834,
                        "y": 7710
                    },
                    "currentGold": 581,
                    "totalGold": 1081,
                    "level": 4,
                    "xp": 1326,
                    "minionsKilled": 18,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13971,
                        "y": 4079
                    },
                    "currentGold": 613,
                    "totalGold": 1113,
                    "level": 3,
                    "xp": 752,
                    "minionsKilled": 17,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 14027,
                        "y": 4488
                    },
                    "currentGold": 472,
                    "totalGold": 972,
                    "level": 3,
                    "xp": 752,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 180184,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 182299,
                    "participantId": 8,
                    "itemId": 2003
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 191811,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 10
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 196269,
                    "participantId": 1,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 202478,
                    "participantId": 5,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 206737,
                    "participantId": 6,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 209182,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 210272,
                    "participantId": 6,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 210371,
                    "participantId": 2,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 210470,
                    "participantId": 3,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 215590,
                    "participantId": 7,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 215689,
                    "participantId": 8,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 217341,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 219818,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 220544,
                    "position": {
                        "x": 1378,
                        "y": 11103
                    },
                    "killerId": 5,
                    "victimId": 9,
                    "assistingParticipantIds": []
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 222957,
                    "participantId": 5,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 223518,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 226922,
                    "participantId": 9,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 227220,
                    "participantId": 6,
                    "itemId": 2003
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 231051,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                }
            ],
            "timestamp": 240036
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 2005,
                        "y": 12148
                    },
                    "currentGold": 148,
                    "totalGold": 1848,
                    "level": 5,
                    "xp": 1734,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 13394,
                        "y": 1480
                    },
                    "currentGold": 1423,
                    "totalGold": 1923,
                    "level": 4,
                    "xp": 1550,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 1234,
                        "y": 732
                    },
                    "currentGold": 30,
                    "totalGold": 1495,
                    "level": 5,
                    "xp": 1936,
                    "minionsKilled": 29,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 7345,
                        "y": 1306
                    },
                    "currentGold": 97,
                    "totalGold": 1347,
                    "level": 3,
                    "xp": 977,
                    "minionsKilled": 24,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 9315,
                        "y": 1489
                    },
                    "currentGold": 64,
                    "totalGold": 1334,
                    "level": 3,
                    "xp": 1037,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 2632,
                        "y": 12877
                    },
                    "currentGold": 447,
                    "totalGold": 1347,
                    "level": 4,
                    "xp": 1719,
                    "minionsKilled": 24,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 5974,
                        "y": 12414
                    },
                    "currentGold": 1035,
                    "totalGold": 1535,
                    "level": 4,
                    "xp": 1379,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8206,
                        "y": 7981
                    },
                    "currentGold": 226,
                    "totalGold": 1301,
                    "level": 5,
                    "xp": 1959,
                    "minionsKilled": 24,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13365,
                        "y": 2872
                    },
                    "currentGold": 852,
                    "totalGold": 2052,
                    "level": 4,
                    "xp": 1421,
                    "minionsKilled": 27,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13470,
                        "y": 2140
                    },
                    "currentGold": 1046,
                    "totalGold": 1546,
                    "level": 4,
                    "xp": 1421,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 247967,
                    "participantId": 5,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 249255,
                    "participantId": 5,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 249552,
                    "participantId": 5,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 250080,
                    "participantId": 7,
                    "itemId": 2010
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 254803,
                    "participantId": 1,
                    "itemId": 2010
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 257975,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 260288,
                    "position": {
                        "x": 12947,
                        "y": 3059
                    },
                    "killerId": 8,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 260321,
                    "participantId": 9,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 262236,
                    "participantId": 3,
                    "itemId": 2010
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 266002,
                    "position": {
                        "x": 13119,
                        "y": 2464
                    },
                    "killerId": 8,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 266795,
                    "participantId": 10,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 270429,
                    "participantId": 3,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 270793,
                    "participantId": 3,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 272281,
                    "participantId": 3,
                    "itemId": 2010
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 272847,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 272980,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 273611,
                    "participantId": 2,
                    "itemId": 1001
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 273644,
                    "participantId": 7,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 274007,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 274139,
                    "participantId": 1,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 274634,
                    "participantId": 8,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 277276,
                    "participantId": 2,
                    "afterId": 0,
                    "beforeId": 1042
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 277541,
                    "participantId": 4,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 278862,
                    "participantId": 2,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 281339,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 281571,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 286063,
                    "participantId": 6,
                    "itemId": 2033
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 286657,
                    "participantId": 6,
                    "itemId": 2055
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 294156,
                    "position": {
                        "x": 13365,
                        "y": 2872
                    },
                    "killerId": 4,
                    "victimId": 8,
                    "assistingParticipantIds": []
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 295972,
                    "participantId": 1,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 296236,
                    "participantId": 1,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 297426,
                    "participantId": 8,
                    "itemId": 3133
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 297823,
                    "participantId": 5,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 298120,
                    "participantId": 1,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 298252,
                    "participantId": 6,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 298450,
                    "participantId": 8,
                    "afterId": 0,
                    "beforeId": 3133
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 299177,
                    "participantId": 8,
                    "itemId": 3057
                }
            ],
            "timestamp": 300036
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 2017,
                        "y": 12070
                    },
                    "currentGold": 410,
                    "totalGold": 2110,
                    "level": 5,
                    "xp": 2274,
                    "minionsKilled": 21,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 9708,
                        "y": 3396
                    },
                    "currentGold": 321,
                    "totalGold": 2346,
                    "level": 5,
                    "xp": 1808,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7711,
                        "y": 7440
                    },
                    "currentGold": 307,
                    "totalGold": 1782,
                    "level": 5,
                    "xp": 2389,
                    "minionsKilled": 36,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 11151,
                        "y": 1052
                    },
                    "currentGold": 353,
                    "totalGold": 1603,
                    "level": 4,
                    "xp": 1358,
                    "minionsKilled": 32,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 11383,
                        "y": 1504
                    },
                    "currentGold": 287,
                    "totalGold": 1557,
                    "level": 4,
                    "xp": 1360,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 2620,
                        "y": 12158
                    },
                    "currentGold": 654,
                    "totalGold": 1554,
                    "level": 5,
                    "xp": 2110,
                    "minionsKilled": 29,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 11750,
                        "y": 1444
                    },
                    "currentGold": 133,
                    "totalGold": 1658,
                    "level": 4,
                    "xp": 1416,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8592,
                        "y": 8168
                    },
                    "currentGold": 496,
                    "totalGold": 1571,
                    "level": 6,
                    "xp": 2471,
                    "minionsKilled": 32,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 12525,
                        "y": 1816
                    },
                    "currentGold": 175,
                    "totalGold": 2175,
                    "level": 4,
                    "xp": 1421,
                    "minionsKilled": 27,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 12283,
                        "y": 1812
                    },
                    "currentGold": 416,
                    "totalGold": 1741,
                    "level": 4,
                    "xp": 1459,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 300844,
                    "participantId": 8,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 302297,
                    "participantId": 8,
                    "itemId": 1036
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 302363,
                    "participantId": 9,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 303519,
                    "participantId": 8,
                    "itemId": 2031
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 307053,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 9
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 307747,
                    "position": {
                        "x": 13332,
                        "y": 3494
                    },
                    "killerId": 4,
                    "victimId": 7,
                    "assistingParticipantIds": []
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 310389,
                    "participantId": 10,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 310653,
                    "participantId": 10,
                    "itemId": 1036
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 311115,
                    "participantId": 4,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 311678,
                    "participantId": 10,
                    "itemId": 1001
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 311843,
                    "participantId": 3,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 313395,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 313395,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 314056,
                    "participantId": 10,
                    "itemId": 3364
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 314056,
                    "participantId": 10,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 315609,
                    "participantId": 7,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 316864,
                    "participantId": 7,
                    "itemId": 1027
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 317491,
                    "participantId": 2,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 317987,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 318317,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 320399,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 322843,
                    "participantId": 4,
                    "itemId": 3006
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 327169,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 329415,
                    "participantId": 4,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 340618,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 340618,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 345176,
                    "participantId": 6,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 357529,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 8
                }
            ],
            "timestamp": 360039
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 3379,
                        "y": 13037
                    },
                    "currentGold": 808,
                    "totalGold": 2508,
                    "level": 6,
                    "xp": 2938,
                    "minionsKilled": 34,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 7524,
                        "y": 5208
                    },
                    "currentGold": 564,
                    "totalGold": 2589,
                    "level": 5,
                    "xp": 2268,
                    "minionsKilled": 2,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8066,
                        "y": 7742
                    },
                    "currentGold": 545,
                    "totalGold": 2020,
                    "level": 6,
                    "xp": 2930,
                    "minionsKilled": 42,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 980,
                        "y": 472
                    },
                    "currentGold": 182,
                    "totalGold": 2132,
                    "level": 5,
                    "xp": 1804,
                    "minionsKilled": 34,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 10864,
                        "y": 3595
                    },
                    "currentGold": 1097,
                    "totalGold": 2367,
                    "level": 5,
                    "xp": 1760,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 4384,
                        "y": 13582
                    },
                    "currentGold": 863,
                    "totalGold": 1763,
                    "level": 6,
                    "xp": 2684,
                    "minionsKilled": 31,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 10972,
                        "y": 8406
                    },
                    "currentGold": 410,
                    "totalGold": 1935,
                    "level": 5,
                    "xp": 1782,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 35,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8598,
                        "y": 8463
                    },
                    "currentGold": 765,
                    "totalGold": 1850,
                    "level": 6,
                    "xp": 3045,
                    "minionsKilled": 38,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13709,
                        "y": 4368
                    },
                    "currentGold": 395,
                    "totalGold": 2395,
                    "level": 5,
                    "xp": 1720,
                    "minionsKilled": 33,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13390,
                        "y": 4466
                    },
                    "currentGold": 590,
                    "totalGold": 1915,
                    "level": 4,
                    "xp": 1577,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 364633,
                    "participantId": 1,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 365558,
                    "participantId": 3,
                    "itemId": 2010
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 366086,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 367772,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 368993,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 369753,
                    "participantId": 5,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 372164,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 374841,
                    "position": {
                        "x": 13524,
                        "y": 3503
                    },
                    "killerId": 3,
                    "victimId": 8,
                    "assistingParticipantIds": [
                        4,
                        2
                    ]
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 374841,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 4
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 374841,
                    "participantId": 4,
                    "itemId": 2055
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 380622,
                    "position": {
                        "x": 13848,
                        "y": 4033
                    },
                    "killerId": 3,
                    "victimId": 7,
                    "assistingParticipantIds": [
                        2
                    ]
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 381648,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 385615,
                    "participantId": 9,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 387366,
                    "participantId": 3,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 397111,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 400547,
                    "wardType": "CONTROL_WARD",
                    "killerId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 404972,
                    "participantId": 2,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 411710,
                    "position": {
                        "x": 9866,
                        "y": 4414
                    },
                    "killerId": 4,
                    "monsterType": "DRAGON",
                    "monsterSubType": "FIRE_DRAGON"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 413627,
                    "participantId": 3,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 416336,
                    "participantId": 2,
                    "itemId": 1036
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 416435,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 416732,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 418186,
                    "participantId": 1,
                    "itemId": 2010
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 419871,
                    "participantId": 2,
                    "itemId": 2003
                }
            ],
            "timestamp": 420072
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 3244,
                        "y": 13095
                    },
                    "currentGold": 1595,
                    "totalGold": 3295,
                    "level": 8,
                    "xp": 4124,
                    "minionsKilled": 47,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 13591,
                        "y": 1428
                    },
                    "currentGold": 1081,
                    "totalGold": 3106,
                    "level": 6,
                    "xp": 2679,
                    "minionsKilled": 2,
                    "jungleMinionsKilled": 36,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8154,
                        "y": 7886
                    },
                    "currentGold": 1153,
                    "totalGold": 2638,
                    "level": 7,
                    "xp": 4028,
                    "minionsKilled": 51,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 12375,
                        "y": 1480
                    },
                    "currentGold": 325,
                    "totalGold": 2325,
                    "level": 5,
                    "xp": 2215,
                    "minionsKilled": 38,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13016,
                        "y": 2103
                    },
                    "currentGold": 583,
                    "totalGold": 2678,
                    "level": 5,
                    "xp": 1927,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 3872,
                        "y": 13551
                    },
                    "currentGold": 187,
                    "totalGold": 1962,
                    "level": 6,
                    "xp": 2969,
                    "minionsKilled": 36,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 5155,
                        "y": 13199
                    },
                    "currentGold": 622,
                    "totalGold": 2147,
                    "level": 5,
                    "xp": 2352,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 40,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8350,
                        "y": 7979
                    },
                    "currentGold": 252,
                    "totalGold": 2132,
                    "level": 7,
                    "xp": 3524,
                    "minionsKilled": 44,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13444,
                        "y": 3260
                    },
                    "currentGold": 768,
                    "totalGold": 2768,
                    "level": 5,
                    "xp": 2175,
                    "minionsKilled": 45,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13644,
                        "y": 1510
                    },
                    "currentGold": 806,
                    "totalGold": 2131,
                    "level": 5,
                    "xp": 1973,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 420502,
                    "participantId": 3,
                    "itemId": 3862
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 420535,
                    "participantId": 10,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 424634,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 426318,
                    "participantId": 8,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 429820,
                    "participantId": 9,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 430810,
                    "participantId": 3,
                    "itemId": 6670
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 430810,
                    "participantId": 3,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 430810,
                    "participantId": 3,
                    "itemId": 1036
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 431702,
                    "participantId": 6,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 432528,
                    "participantId": 1,
                    "itemId": 2010
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 432990,
                    "participantId": 4,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 434213,
                    "participantId": 5,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 434510,
                    "participantId": 3,
                    "itemId": 2031
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 434972,
                    "participantId": 3,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 435005,
                    "participantId": 1,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 435997,
                    "participantId": 3,
                    "itemId": 3364
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 435997,
                    "participantId": 3,
                    "itemId": 3340
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 438606,
                    "participantId": 7,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 444992,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 444992,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 459214,
                    "position": {
                        "x": 8350,
                        "y": 7979
                    },
                    "killerId": 1,
                    "victimId": 6,
                    "assistingParticipantIds": []
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 462290,
                    "participantId": 7,
                    "itemId": 3850
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 465467,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 472509,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 473667,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 473898,
                    "participantId": 7,
                    "itemId": 2010
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 474262,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 474460,
                    "position": {
                        "x": 3872,
                        "y": 13551
                    },
                    "killerId": 5,
                    "victimId": 9,
                    "assistingParticipantIds": []
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 477534,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 478262,
                    "position": {
                        "x": 13644,
                        "y": 1510
                    },
                    "killerId": 4,
                    "victimId": 7,
                    "assistingParticipantIds": [
                        3
                    ]
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 479186,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 479285,
                    "participantId": 5,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 479384,
                    "participantId": 6,
                    "itemId": 1027
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 479814,
                    "participantId": 6,
                    "itemId": 1052
                }
            ],
            "timestamp": 480078
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 1452,
                        "y": 8426
                    },
                    "currentGold": 83,
                    "totalGold": 3683,
                    "level": 8,
                    "xp": 4395,
                    "minionsKilled": 53,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 3570,
                        "y": 7998
                    },
                    "currentGold": 126,
                    "totalGold": 3326,
                    "level": 6,
                    "xp": 2956,
                    "minionsKilled": 2,
                    "jungleMinionsKilled": 40,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6933,
                        "y": 7249
                    },
                    "currentGold": 309,
                    "totalGold": 3084,
                    "level": 8,
                    "xp": 4362,
                    "minionsKilled": 57,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 13416,
                        "y": 3801
                    },
                    "currentGold": 722,
                    "totalGold": 2722,
                    "level": 6,
                    "xp": 2750,
                    "minionsKilled": 50,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13641,
                        "y": 3831
                    },
                    "currentGold": 901,
                    "totalGold": 2996,
                    "level": 6,
                    "xp": 2444,
                    "minionsKilled": 4,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 1486,
                        "y": 11208
                    },
                    "currentGold": 466,
                    "totalGold": 2241,
                    "level": 7,
                    "xp": 3392,
                    "minionsKilled": 42,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 12011,
                        "y": 7671
                    },
                    "currentGold": 345,
                    "totalGold": 2395,
                    "level": 6,
                    "xp": 2588,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 44,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7855,
                        "y": 7937
                    },
                    "currentGold": 507,
                    "totalGold": 2397,
                    "level": 7,
                    "xp": 3917,
                    "minionsKilled": 49,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 14110,
                        "y": 4661
                    },
                    "currentGold": 1019,
                    "totalGold": 3019,
                    "level": 6,
                    "xp": 2460,
                    "minionsKilled": 51,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13184,
                        "y": 5000
                    },
                    "currentGold": 187,
                    "totalGold": 2312,
                    "level": 5,
                    "xp": 2160,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_KILL",
                    "timestamp": 480177,
                    "wardType": "CONTROL_WARD",
                    "killerId": 8
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 481036,
                    "participantId": 2,
                    "itemId": 2003
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 482888,
                    "wardType": "YELLOW_TRINKET",
                    "killerId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 485069,
                    "participantId": 1,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 485168,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 485168,
                    "participantId": 3,
                    "itemId": 2055
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 487678,
                    "wardType": "SIGHT_WARD",
                    "killerId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 489857,
                    "participantId": 10,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 493790,
                    "participantId": 7,
                    "itemId": 3020
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 493790,
                    "participantId": 7,
                    "itemId": 1001
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 498185,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 502082,
                    "participantId": 2,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 505551,
                    "participantId": 1,
                    "itemId": 3802
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 505551,
                    "participantId": 1,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 505551,
                    "participantId": 1,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 506244,
                    "participantId": 1,
                    "itemId": 1026
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 508589,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 512718,
                    "participantId": 4,
                    "itemId": 3134
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 512718,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 513346,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 514336,
                    "participantId": 5,
                    "itemId": 6029
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 515492,
                    "participantId": 5,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 515855,
                    "participantId": 4,
                    "itemId": 2055
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 517573,
                    "wardType": "CONTROL_WARD",
                    "killerId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 518002,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 9
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 518530,
                    "participantId": 10,
                    "itemId": 3051
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 518530,
                    "participantId": 10,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 518530,
                    "participantId": 10,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 518596,
                    "participantId": 5,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 521041,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 529794,
                    "participantId": 9,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 530851,
                    "participantId": 3,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 538645,
                    "participantId": 8,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 540105
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 3871,
                        "y": 13866
                    },
                    "currentGold": 654,
                    "totalGold": 4254,
                    "level": 9,
                    "xp": 5240,
                    "minionsKilled": 67,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 4745,
                        "y": 10278
                    },
                    "currentGold": 519,
                    "totalGold": 3719,
                    "level": 7,
                    "xp": 3508,
                    "minionsKilled": 2,
                    "jungleMinionsKilled": 52,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 10958,
                        "y": 4303
                    },
                    "currentGold": 1161,
                    "totalGold": 3936,
                    "level": 9,
                    "xp": 5184,
                    "minionsKilled": 69,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 12172,
                        "y": 1518
                    },
                    "currentGold": 5,
                    "totalGold": 3555,
                    "level": 6,
                    "xp": 3119,
                    "minionsKilled": 52,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 6251,
                        "y": 1174
                    },
                    "currentGold": 321,
                    "totalGold": 3366,
                    "level": 6,
                    "xp": 2679,
                    "minionsKilled": 4,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 4173,
                        "y": 13767
                    },
                    "currentGold": 630,
                    "totalGold": 2405,
                    "level": 7,
                    "xp": 3634,
                    "minionsKilled": 44,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 10714,
                        "y": 12578
                    },
                    "currentGold": 87,
                    "totalGold": 2612,
                    "level": 6,
                    "xp": 2702,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 44,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 6606,
                        "y": 6838
                    },
                    "currentGold": 804,
                    "totalGold": 2694,
                    "level": 8,
                    "xp": 4488,
                    "minionsKilled": 59,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13920,
                        "y": 10375
                    },
                    "currentGold": 14,
                    "totalGold": 3804,
                    "level": 6,
                    "xp": 2916,
                    "minionsKilled": 55,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13322,
                        "y": 1108
                    },
                    "currentGold": 292,
                    "totalGold": 2927,
                    "level": 6,
                    "xp": 2616,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 547538,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 554408,
                    "participantId": 6,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 555763,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 555763,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 557745,
                    "participantId": 4,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 559990,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 1
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 559990,
                    "participantId": 1,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 570294,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 570526,
                    "position": {
                        "x": 10681,
                        "y": 1235
                    },
                    "killerId": 8,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        10,
                        7
                    ]
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 570526,
                    "participantId": 7,
                    "itemId": 2419
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 571286,
                    "position": {
                        "x": 11833,
                        "y": 1614
                    },
                    "killerId": 1,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        2,
                        3
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 572441,
                    "participantId": 7,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 574688,
                    "position": {
                        "x": 11008,
                        "y": 1736
                    },
                    "killerId": 2,
                    "victimId": 8,
                    "assistingParticipantIds": [
                        1,
                        3
                    ]
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 577001,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 579813,
                    "participantId": 8,
                    "itemId": 1055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 580176,
                    "participantId": 3,
                    "itemId": 1037
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 582062,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 4
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 582062,
                    "participantId": 4,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 584772,
                    "participantId": 5,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 584937,
                    "position": {
                        "x": 12172,
                        "y": 1518
                    },
                    "killerId": 7,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        8
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 584937,
                    "position": {
                        "x": 13322,
                        "y": 1108
                    },
                    "killerId": 2,
                    "victimId": 7,
                    "assistingParticipantIds": [
                        1
                    ]
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 586692,
                    "participantId": 8,
                    "afterId": 1055,
                    "beforeId": 0
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 587785,
                    "participantId": 3,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 588412,
                    "participantId": 8,
                    "itemId": 2031
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 589371,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 590165,
                    "participantId": 2,
                    "itemId": 6670
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 590165,
                    "participantId": 2,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 590165,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 590165,
                    "participantId": 2,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 592148,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 592445,
                    "participantId": 1,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 593403,
                    "participantId": 5,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 593766,
                    "participantId": 8,
                    "itemId": 3508
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 593766,
                    "participantId": 8,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 593766,
                    "participantId": 8,
                    "itemId": 3057
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 594295,
                    "participantId": 7,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 594691,
                    "participantId": 2,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 595650,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 596673,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 598259,
                    "participantId": 7,
                    "afterId": 0,
                    "beforeId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 598623,
                    "participantId": 2,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 599151,
                    "participantId": 7,
                    "itemId": 2055
                }
            ],
            "timestamp": 600109
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 6616,
                        "y": 13515
                    },
                    "currentGold": 1779,
                    "totalGold": 5379,
                    "level": 10,
                    "xp": 6219,
                    "minionsKilled": 81,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 7575,
                        "y": 11067
                    },
                    "currentGold": 1335,
                    "totalGold": 4535,
                    "level": 8,
                    "xp": 4283,
                    "minionsKilled": 6,
                    "jungleMinionsKilled": 60,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 3265,
                        "y": 3553
                    },
                    "currentGold": 171,
                    "totalGold": 4281,
                    "level": 9,
                    "xp": 5697,
                    "minionsKilled": 76,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 11935,
                        "y": 2047
                    },
                    "currentGold": 337,
                    "totalGold": 3887,
                    "level": 7,
                    "xp": 3368,
                    "minionsKilled": 58,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 12513,
                        "y": 1757
                    },
                    "currentGold": 683,
                    "totalGold": 3728,
                    "level": 6,
                    "xp": 3140,
                    "minionsKilled": 9,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 12078,
                        "y": 14127
                    },
                    "currentGold": 106,
                    "totalGold": 2556,
                    "level": 7,
                    "xp": 3934,
                    "minionsKilled": 46,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 8572,
                        "y": 12714
                    },
                    "currentGold": 249,
                    "totalGold": 2774,
                    "level": 6,
                    "xp": 2808,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 45,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7955,
                        "y": 7564
                    },
                    "currentGold": 1132,
                    "totalGold": 3032,
                    "level": 9,
                    "xp": 5062,
                    "minionsKilled": 68,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 12790,
                        "y": 2765
                    },
                    "currentGold": 380,
                    "totalGold": 4170,
                    "level": 7,
                    "xp": 3331,
                    "minionsKilled": 66,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13294,
                        "y": 2400
                    },
                    "currentGold": 452,
                    "totalGold": 3087,
                    "level": 6,
                    "xp": 2880,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 612402,
                    "participantId": 10,
                    "itemId": 1035
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 612633,
                    "position": {
                        "x": 4582,
                        "y": 10320
                    },
                    "killerId": 4,
                    "monsterType": "RIFTHERALD"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 614286,
                    "participantId": 4,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 624560,
                    "participantId": 4,
                    "itemId": 3513
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 626178,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 632620,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 634668,
                    "position": {
                        "x": 7204,
                        "y": 13768
                    },
                    "killerId": 4,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        5
                    ]
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 637046,
                    "wardType": "SIGHT_WARD",
                    "killerId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 638301,
                    "participantId": 9,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 638301,
                    "participantId": 9,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 638301,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 638896,
                    "participantId": 9,
                    "itemId": 6029
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 638896,
                    "participantId": 9,
                    "itemId": 1037
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 641704,
                    "participantId": 2,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 643256,
                    "participantId": 8,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 644709,
                    "participantId": 4,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 645271,
                    "participantId": 1,
                    "itemId": 6655
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 645271,
                    "participantId": 1,
                    "itemId": 3802
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 645271,
                    "participantId": 1,
                    "itemId": 1026
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 647318,
                    "participantId": 1,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 647912,
                    "participantId": 1,
                    "itemId": 3363
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 647912,
                    "participantId": 1,
                    "itemId": 3340
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 648309,
                    "position": {
                        "x": 4318,
                        "y": 13875
                    },
                    "killerId": 4,
                    "assistingParticipantIds": [],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "TOP_LANE",
                    "towerType": "OUTER_TURRET"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 652834,
                    "participantId": 6,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 656666,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 656666,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 658384,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                }
            ],
            "timestamp": 660139
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 6019,
                        "y": 13508
                    },
                    "currentGold": 2434,
                    "totalGold": 6034,
                    "level": 10,
                    "xp": 6600,
                    "minionsKilled": 84,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 3437,
                        "y": 2131
                    },
                    "currentGold": 774,
                    "totalGold": 4724,
                    "level": 8,
                    "xp": 4440,
                    "minionsKilled": 6,
                    "jungleMinionsKilled": 64,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7144,
                        "y": 9302
                    },
                    "currentGold": 857,
                    "totalGold": 4967,
                    "level": 10,
                    "xp": 6187,
                    "minionsKilled": 82,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 13142,
                        "y": 3452
                    },
                    "currentGold": 683,
                    "totalGold": 4233,
                    "level": 7,
                    "xp": 3824,
                    "minionsKilled": 71,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13198,
                        "y": 3798
                    },
                    "currentGold": 1193,
                    "totalGold": 4238,
                    "level": 7,
                    "xp": 3596,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 7825,
                        "y": 12108
                    },
                    "currentGold": 176,
                    "totalGold": 3426,
                    "level": 8,
                    "xp": 4213,
                    "minionsKilled": 48,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 14340,
                        "y": 14391
                    },
                    "currentGold": 580,
                    "totalGold": 3105,
                    "level": 7,
                    "xp": 3503,
                    "minionsKilled": 5,
                    "jungleMinionsKilled": 45,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 13418,
                        "y": 13891
                    },
                    "currentGold": 1359,
                    "totalGold": 3259,
                    "level": 9,
                    "xp": 5332,
                    "minionsKilled": 74,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 14027,
                        "y": 4864
                    },
                    "currentGold": 741,
                    "totalGold": 4531,
                    "level": 7,
                    "xp": 3708,
                    "minionsKilled": 76,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13522,
                        "y": 4568
                    },
                    "currentGold": 653,
                    "totalGold": 3288,
                    "level": 7,
                    "xp": 3282,
                    "minionsKilled": 0,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 660469,
                    "participantId": 5,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 662550,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 662881,
                    "wardType": "SIGHT_WARD",
                    "killerId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 665291,
                    "participantId": 3,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 666480,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 667969,
                    "participantId": 10,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 675664,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 685939,
                    "position": {
                        "x": 7303,
                        "y": 11288
                    },
                    "killerId": 9,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        10
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 688316,
                    "participantId": 9,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 688416,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 688416,
                    "participantId": 2,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 690893,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 694098,
                    "participantId": 4,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 694098,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 699026,
                    "position": {
                        "x": 7270,
                        "y": 12360
                    },
                    "killerId": 5,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        1
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 700975,
                    "position": {
                        "x": 7825,
                        "y": 12108
                    },
                    "killerId": 1,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        5
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 703288,
                    "participantId": 1,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 707944,
                    "participantId": 9,
                    "itemId": 3067
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 708672,
                    "participantId": 7,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 711315,
                    "wardType": "CONTROL_WARD",
                    "killerId": 1
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 717956,
                    "participantId": 10,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 717956,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 719938,
                    "participantId": 10,
                    "afterId": 0,
                    "beforeId": 3067
                }
            ],
            "timestamp": 720169
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 8693,
                        "y": 5047
                    },
                    "currentGold": 77,
                    "totalGold": 6177,
                    "level": 10,
                    "xp": 6934,
                    "minionsKilled": 85,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 11841,
                        "y": 3389
                    },
                    "currentGold": 46,
                    "totalGold": 4996,
                    "level": 8,
                    "xp": 4747,
                    "minionsKilled": 6,
                    "jungleMinionsKilled": 68,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8859,
                        "y": 5564
                    },
                    "currentGold": 328,
                    "totalGold": 5173,
                    "level": 10,
                    "xp": 6667,
                    "minionsKilled": 88,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 10836,
                        "y": 3411
                    },
                    "currentGold": 552,
                    "totalGold": 4602,
                    "level": 8,
                    "xp": 4130,
                    "minionsKilled": 76,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 10465,
                        "y": 3558
                    },
                    "currentGold": 1802,
                    "totalGold": 4846,
                    "level": 7,
                    "xp": 3901,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 11578,
                        "y": 3689
                    },
                    "currentGold": 268,
                    "totalGold": 3718,
                    "level": 8,
                    "xp": 4653,
                    "minionsKilled": 48,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 10302,
                        "y": 4844
                    },
                    "currentGold": 547,
                    "totalGold": 3547,
                    "level": 7,
                    "xp": 3755,
                    "minionsKilled": 5,
                    "jungleMinionsKilled": 45,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 9827,
                        "y": 5242
                    },
                    "currentGold": 381,
                    "totalGold": 3606,
                    "level": 9,
                    "xp": 5936,
                    "minionsKilled": 84,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 10881,
                        "y": 4814
                    },
                    "currentGold": 563,
                    "totalGold": 4953,
                    "level": 7,
                    "xp": 3815,
                    "minionsKilled": 76,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 11437,
                        "y": 5571
                    },
                    "currentGold": 1033,
                    "totalGold": 3668,
                    "level": 7,
                    "xp": 3860,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 721094,
                    "participantId": 10,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 721094,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 721556,
                    "participantId": 6,
                    "itemId": 3802
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 721556,
                    "participantId": 6,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 721556,
                    "participantId": 6,
                    "itemId": 1027
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 722910,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 724132,
                    "participantId": 6,
                    "itemId": 3020
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 724132,
                    "participantId": 6,
                    "itemId": 2422
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 732065,
                    "participantId": 9,
                    "itemId": 6630
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 732065,
                    "participantId": 9,
                    "itemId": 6029
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 732065,
                    "participantId": 9,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 732065,
                    "participantId": 9,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 734018,
                    "participantId": 8,
                    "itemId": 3158
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 734018,
                    "participantId": 8,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 739511,
                    "participantId": 5,
                    "itemId": 6630
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 739511,
                    "participantId": 5,
                    "itemId": 6029
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 739511,
                    "participantId": 5,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 739511,
                    "participantId": 5,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 740403,
                    "participantId": 5,
                    "itemId": 3047
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 740403,
                    "participantId": 5,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 743114,
                    "participantId": 5,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 743576,
                    "participantId": 1,
                    "itemId": 1001
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 744040,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 6
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 744040,
                    "participantId": 6,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 746024,
                    "participantId": 1,
                    "itemId": 1052
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 759506,
                    "position": {
                        "x": 10836,
                        "y": 3411
                    },
                    "killerId": 8,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        9,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 759969,
                    "position": {
                        "x": 11578,
                        "y": 3689
                    },
                    "killerId": 3,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        4,
                        2
                    ]
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 762943,
                    "participantId": 7,
                    "itemId": 2423
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 763636,
                    "position": {
                        "x": 11841,
                        "y": 3389
                    },
                    "killerId": 10,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        9,
                        7
                    ]
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 764264,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 766014,
                    "participantId": 3,
                    "itemId": 3863
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 767370,
                    "participantId": 2,
                    "itemId": 3006
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 767370,
                    "participantId": 2,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 767370,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 767865,
                    "participantId": 4,
                    "itemId": 6691
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 767865,
                    "participantId": 4,
                    "itemId": 3134
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 767865,
                    "participantId": 4,
                    "itemId": 3133
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 767965,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 767965,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 771962,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 771962,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 774240,
                    "wardType": "SIGHT_WARD",
                    "killerId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 774240,
                    "participantId": 2,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 780190
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 718,
                        "y": 3365
                    },
                    "currentGold": 300,
                    "totalGold": 6400,
                    "level": 10,
                    "xp": 6995,
                    "minionsKilled": 85,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 11062,
                        "y": 4366
                    },
                    "currentGold": 169,
                    "totalGold": 5119,
                    "level": 8,
                    "xp": 4747,
                    "minionsKilled": 6,
                    "jungleMinionsKilled": 68,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 5540,
                        "y": 5609
                    },
                    "currentGold": 755,
                    "totalGold": 5600,
                    "level": 10,
                    "xp": 6732,
                    "minionsKilled": 88,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 12024,
                        "y": 2196
                    },
                    "currentGold": 774,
                    "totalGold": 4824,
                    "level": 8,
                    "xp": 4278,
                    "minionsKilled": 76,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 12838,
                        "y": 2628
                    },
                    "currentGold": 2085,
                    "totalGold": 5130,
                    "level": 8,
                    "xp": 4291,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 852,
                        "y": 10262
                    },
                    "currentGold": 591,
                    "totalGold": 4041,
                    "level": 9,
                    "xp": 5226,
                    "minionsKilled": 56,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 8289,
                        "y": 10098
                    },
                    "currentGold": 53,
                    "totalGold": 3753,
                    "level": 8,
                    "xp": 4062,
                    "minionsKilled": 5,
                    "jungleMinionsKilled": 45,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 13813,
                        "y": 13448
                    },
                    "currentGold": 202,
                    "totalGold": 3937,
                    "level": 10,
                    "xp": 6538,
                    "minionsKilled": 92,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 12986,
                        "y": 3370
                    },
                    "currentGold": 1604,
                    "totalGold": 5994,
                    "level": 8,
                    "xp": 4636,
                    "minionsKilled": 84,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13598,
                        "y": 8029
                    },
                    "currentGold": 503,
                    "totalGold": 3828,
                    "level": 7,
                    "xp": 3951,
                    "minionsKilled": 1,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 790598,
                    "position": {
                        "x": 11132,
                        "y": 5170
                    },
                    "killerId": 1,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        5,
                        3
                    ]
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 798198,
                    "participantId": 5,
                    "itemId": 2003
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 802459,
                    "position": {
                        "x": 8809,
                        "y": 5536
                    },
                    "killerId": 8,
                    "victimId": 5,
                    "assistingParticipantIds": [
                        10,
                        6
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 804176,
                    "participantId": 8,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 804243,
                    "participantId": 6,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 805829,
                    "position": {
                        "x": 10372,
                        "y": 5057
                    },
                    "killerId": 8,
                    "monsterType": "DRAGON",
                    "monsterSubType": "EARTH_DRAGON"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 806556,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 817326,
                    "participantId": 7,
                    "itemId": 3802
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 817326,
                    "participantId": 7,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 817326,
                    "participantId": 7,
                    "itemId": 1027
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 818054,
                    "participantId": 10,
                    "itemId": 3057
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 819375,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 819606,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 820200,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 820630,
                    "participantId": 7,
                    "itemId": 3364
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 820630,
                    "participantId": 7,
                    "itemId": 3340
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 826114,
                    "participantId": 9,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 833577,
                    "participantId": 3,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 836847,
                    "participantId": 6,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 838696,
                    "participantId": 6,
                    "itemId": 2055
                }
            ],
            "timestamp": 840217
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 7257,
                        "y": 13734
                    },
                    "currentGold": 696,
                    "totalGold": 6796,
                    "level": 11,
                    "xp": 7750,
                    "minionsKilled": 97,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 12072,
                        "y": 8977
                    },
                    "currentGold": 183,
                    "totalGold": 5483,
                    "level": 9,
                    "xp": 5214,
                    "minionsKilled": 7,
                    "jungleMinionsKilled": 76,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7522,
                        "y": 7872
                    },
                    "currentGold": 1223,
                    "totalGold": 6068,
                    "level": 11,
                    "xp": 7428,
                    "minionsKilled": 96,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 13360,
                        "y": 2542
                    },
                    "currentGold": 1587,
                    "totalGold": 5637,
                    "level": 9,
                    "xp": 5258,
                    "minionsKilled": 89,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 7694,
                        "y": 1345
                    },
                    "currentGold": 274,
                    "totalGold": 5644,
                    "level": 8,
                    "xp": 4664,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 7727,
                        "y": 13498
                    },
                    "currentGold": 804,
                    "totalGold": 4254,
                    "level": 9,
                    "xp": 5678,
                    "minionsKilled": 61,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 9108,
                        "y": 9032
                    },
                    "currentGold": 555,
                    "totalGold": 4255,
                    "level": 8,
                    "xp": 4526,
                    "minionsKilled": 5,
                    "jungleMinionsKilled": 49,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 9078,
                        "y": 8674
                    },
                    "currentGold": 573,
                    "totalGold": 4308,
                    "level": 10,
                    "xp": 6997,
                    "minionsKilled": 95,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13811,
                        "y": 4309
                    },
                    "currentGold": 381,
                    "totalGold": 6221,
                    "level": 8,
                    "xp": 4732,
                    "minionsKilled": 86,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13722,
                        "y": 4590
                    },
                    "currentGold": 727,
                    "totalGold": 4052,
                    "level": 8,
                    "xp": 4489,
                    "minionsKilled": 5,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 841572,
                    "participantId": 10,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 844682,
                    "position": {
                        "x": 13675,
                        "y": 3894
                    },
                    "killerId": 3,
                    "victimId": 8,
                    "assistingParticipantIds": [
                        2
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 848018,
                    "participantId": 8,
                    "itemId": 3134
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 849108,
                    "wardType": "CONTROL_WARD",
                    "killerId": 4
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 849372,
                    "participantId": 8,
                    "itemId": 1036
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 859051,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 859580,
                    "participantId": 7,
                    "itemId": 3851
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 861925,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 865828,
                    "wardType": "CONTROL_WARD",
                    "killerId": 2
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 867051,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 867117,
                    "participantId": 4,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 875476,
                    "participantId": 3,
                    "itemId": 6672
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 875476,
                    "participantId": 3,
                    "itemId": 6670
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 875476,
                    "participantId": 3,
                    "itemId": 1037
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 878019,
                    "position": {
                        "x": 12072,
                        "y": 8977
                    },
                    "killerId": 10,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        6
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 879341,
                    "participantId": 5,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 879738,
                    "participantId": 1,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 880036,
                    "participantId": 3,
                    "itemId": 3047
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 880036,
                    "participantId": 3,
                    "itemId": 2422
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 881423,
                    "participantId": 3,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 882909,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 886509,
                    "participantId": 7,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 887103,
                    "participantId": 2,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 891134,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 895791,
                    "position": {
                        "x": 9108,
                        "y": 9032
                    },
                    "killerId": 2,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        1
                    ]
                }
            ],
            "timestamp": 900222
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 7284,
                        "y": 12235
                    },
                    "currentGold": 1833,
                    "totalGold": 7933,
                    "level": 12,
                    "xp": 8787,
                    "minionsKilled": 106,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 7530,
                        "y": 11690
                    },
                    "currentGold": 441,
                    "totalGold": 5741,
                    "level": 9,
                    "xp": 5431,
                    "minionsKilled": 7,
                    "jungleMinionsKilled": 80,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7125,
                        "y": 7484
                    },
                    "currentGold": 1777,
                    "totalGold": 6622,
                    "level": 11,
                    "xp": 8270,
                    "minionsKilled": 108,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 11877,
                        "y": 1721
                    },
                    "currentGold": 385,
                    "totalGold": 5960,
                    "level": 9,
                    "xp": 5485,
                    "minionsKilled": 94,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 11765,
                        "y": 1682
                    },
                    "currentGold": 586,
                    "totalGold": 5956,
                    "level": 9,
                    "xp": 5162,
                    "minionsKilled": 19,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 7612,
                        "y": 13698
                    },
                    "currentGold": 341,
                    "totalGold": 4391,
                    "level": 9,
                    "xp": 5891,
                    "minionsKilled": 62,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 8367,
                        "y": 10135
                    },
                    "currentGold": 782,
                    "totalGold": 4482,
                    "level": 8,
                    "xp": 4797,
                    "minionsKilled": 11,
                    "jungleMinionsKilled": 49,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 9067,
                        "y": 7662
                    },
                    "currentGold": 850,
                    "totalGold": 4585,
                    "level": 11,
                    "xp": 7631,
                    "minionsKilled": 104,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13063,
                        "y": 2048
                    },
                    "currentGold": 777,
                    "totalGold": 6617,
                    "level": 9,
                    "xp": 5277,
                    "minionsKilled": 102,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13613,
                        "y": 2580
                    },
                    "currentGold": 984,
                    "totalGold": 4309,
                    "level": 8,
                    "xp": 4946,
                    "minionsKilled": 7,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 905605,
                    "participantId": 2,
                    "itemId": 6672
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 905605,
                    "participantId": 2,
                    "itemId": 6670
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 905605,
                    "participantId": 2,
                    "itemId": 1037
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 906364,
                    "position": {
                        "x": 7943,
                        "y": 13411
                    },
                    "killerId": 5,
                    "assistingParticipantIds": [],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "TOP_LANE",
                    "towerType": "INNER_TURRET"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 907223,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 907454,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 910889,
                    "position": {
                        "x": 8275,
                        "y": 13328
                    },
                    "killerId": 5,
                    "victimId": 9,
                    "assistingParticipantIds": []
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 911978,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 915646,
                    "participantId": 9,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 916902,
                    "participantId": 9,
                    "itemId": 1029
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 917761,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 919445,
                    "wardType": "CONTROL_WARD",
                    "killerId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 927572,
                    "participantId": 5,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 933584,
                    "participantId": 6,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 934311,
                    "participantId": 8,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 938242,
                    "participantId": 4,
                    "itemId": 1035
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 951229,
                    "participantId": 3,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 954929,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 959720,
                    "participantId": 7,
                    "itemId": 2003
                }
            ],
            "timestamp": 960248
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 5930,
                        "y": 13435
                    },
                    "currentGold": 2098,
                    "totalGold": 8198,
                    "level": 12,
                    "xp": 9055,
                    "minionsKilled": 109,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 4651,
                        "y": 10114
                    },
                    "currentGold": 837,
                    "totalGold": 6137,
                    "level": 9,
                    "xp": 5726,
                    "minionsKilled": 7,
                    "jungleMinionsKilled": 80,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7178,
                        "y": 7284
                    },
                    "currentGold": 237,
                    "totalGold": 7097,
                    "level": 12,
                    "xp": 8994,
                    "minionsKilled": 117,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 6752,
                        "y": 1031
                    },
                    "currentGold": 222,
                    "totalGold": 6172,
                    "level": 9,
                    "xp": 5578,
                    "minionsKilled": 95,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 10683,
                        "y": 1283
                    },
                    "currentGold": 275,
                    "totalGold": 6145,
                    "level": 9,
                    "xp": 5372,
                    "minionsKilled": 22,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 14340,
                        "y": 14391
                    },
                    "currentGold": 68,
                    "totalGold": 4618,
                    "level": 10,
                    "xp": 6222,
                    "minionsKilled": 68,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 12099,
                        "y": 6803
                    },
                    "currentGold": 1064,
                    "totalGold": 4764,
                    "level": 9,
                    "xp": 5216,
                    "minionsKilled": 11,
                    "jungleMinionsKilled": 57,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 9351,
                        "y": 5793
                    },
                    "currentGold": 1239,
                    "totalGold": 4974,
                    "level": 11,
                    "xp": 8269,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 11852,
                        "y": 1248
                    },
                    "currentGold": 1649,
                    "totalGold": 7489,
                    "level": 9,
                    "xp": 5953,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 11967,
                        "y": 1657
                    },
                    "currentGold": 1275,
                    "totalGold": 4600,
                    "level": 9,
                    "xp": 5561,
                    "minionsKilled": 7,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 961801,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 963355,
                    "position": {
                        "x": 12079,
                        "y": 2051
                    },
                    "killerId": 8,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 972272,
                    "participantId": 3,
                    "itemId": 6677
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 972272,
                    "participantId": 3,
                    "itemId": 1042
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 977358,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 6
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 977358,
                    "participantId": 6,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 979240,
                    "participantId": 7,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 986572,
                    "wardType": "CONTROL_WARD",
                    "killerId": 6
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 986935,
                    "position": {
                        "x": 3113,
                        "y": 11870
                    },
                    "killerId": 4,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        1
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 988157,
                    "participantId": 1,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 988520,
                    "participantId": 9,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 990006,
                    "participantId": 9,
                    "itemId": 3047
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 990006,
                    "participantId": 9,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 990006,
                    "participantId": 9,
                    "itemId": 1029
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 991063,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 5
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 998695,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 999620,
                    "participantId": 1,
                    "itemId": 3020
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 999620,
                    "participantId": 1,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1001073,
                    "participantId": 2,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1001502,
                    "participantId": 2,
                    "itemId": 3363
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1001502,
                    "participantId": 2,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1005367,
                    "participantId": 1,
                    "itemId": 2420
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1005929,
                    "participantId": 1,
                    "itemId": 3191
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1005929,
                    "participantId": 1,
                    "itemId": 1052
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1010158,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1017128,
                    "participantId": 10,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 1020268
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 12497,
                        "y": 5753
                    },
                    "currentGold": 352,
                    "totalGold": 8527,
                    "level": 12,
                    "xp": 9449,
                    "minionsKilled": 114,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 12535,
                        "y": 7188
                    },
                    "currentGold": 1190,
                    "totalGold": 6490,
                    "level": 9,
                    "xp": 6035,
                    "minionsKilled": 8,
                    "jungleMinionsKilled": 84,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6661,
                        "y": 6630
                    },
                    "currentGold": 762,
                    "totalGold": 7622,
                    "level": 12,
                    "xp": 9271,
                    "minionsKilled": 121,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 13685,
                        "y": 5308
                    },
                    "currentGold": 849,
                    "totalGold": 6799,
                    "level": 9,
                    "xp": 6026,
                    "minionsKilled": 107,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13201,
                        "y": 5436
                    },
                    "currentGold": 714,
                    "totalGold": 6583,
                    "level": 9,
                    "xp": 5881,
                    "minionsKilled": 25,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 6521,
                        "y": 12252
                    },
                    "currentGold": 341,
                    "totalGold": 4891,
                    "level": 10,
                    "xp": 6695,
                    "minionsKilled": 75,
                    "jungleMinionsKilled": 1,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 13675,
                        "y": 11844
                    },
                    "currentGold": 64,
                    "totalGold": 4972,
                    "level": 9,
                    "xp": 5432,
                    "minionsKilled": 11,
                    "jungleMinionsKilled": 61,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 14210,
                        "y": 13445
                    },
                    "currentGold": 60,
                    "totalGold": 5460,
                    "level": 12,
                    "xp": 9049,
                    "minionsKilled": 125,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 13459,
                        "y": 7526
                    },
                    "currentGold": 1869,
                    "totalGold": 7709,
                    "level": 10,
                    "xp": 6197,
                    "minionsKilled": 120,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13563,
                        "y": 7495
                    },
                    "currentGold": 1443,
                    "totalGold": 4768,
                    "level": 9,
                    "xp": 5805,
                    "minionsKilled": 9,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1029552,
                    "position": {
                        "x": 8955,
                        "y": 8510
                    },
                    "killerId": 1,
                    "assistingParticipantIds": [],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "MID_LANE",
                    "towerType": "OUTER_TURRET"
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 1029783,
                    "position": {
                        "x": 4582,
                        "y": 10270
                    },
                    "killerId": 4,
                    "monsterType": "RIFTHERALD"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1032228,
                    "participantId": 8,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1033219,
                    "participantId": 4,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1036555,
                    "participantId": 5,
                    "itemId": 3053
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1036555,
                    "participantId": 5,
                    "itemId": 3044
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1037513,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 1
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1037513,
                    "participantId": 1,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1038173,
                    "participantId": 6,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1038305,
                    "participantId": 5,
                    "itemId": 2055
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1041741,
                    "wardType": "YELLOW_TRINKET",
                    "killerId": 1
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1044318,
                    "wardType": "CONTROL_WARD",
                    "killerId": 4
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1062486,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1062750,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1066185,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1066581,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1066581,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1067242,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 5
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1067242,
                    "participantId": 5,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1067374,
                    "participantId": 10,
                    "itemId": 3078
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1067374,
                    "participantId": 10,
                    "itemId": 3057
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1067374,
                    "participantId": 10,
                    "itemId": 3051
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1067374,
                    "participantId": 10,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1071969,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1072696,
                    "position": {
                        "x": 13866,
                        "y": 4505
                    },
                    "killerId": 2,
                    "assistingParticipantIds": [
                        3
                    ],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "BOT_LANE",
                    "towerType": "OUTER_TURRET"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1073854,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1075277,
                    "participantId": 6,
                    "itemId": 6653
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1075277,
                    "participantId": 6,
                    "itemId": 3802
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1075277,
                    "participantId": 6,
                    "itemId": 1052
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1078645,
                    "wardType": "CONTROL_WARD",
                    "killerId": 5
                }
            ],
            "timestamp": 1080296
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 13985,
                        "y": 10044
                    },
                    "currentGold": 1505,
                    "totalGold": 9680,
                    "level": 13,
                    "xp": 10068,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 13504,
                        "y": 8135
                    },
                    "currentGold": 204,
                    "totalGold": 7129,
                    "level": 10,
                    "xp": 6570,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 84,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 9108,
                        "y": 8363
                    },
                    "currentGold": 32,
                    "totalGold": 7842,
                    "level": 12,
                    "xp": 9542,
                    "minionsKilled": 124,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 1806,
                        "y": 1366
                    },
                    "currentGold": 357,
                    "totalGold": 7057,
                    "level": 10,
                    "xp": 6390,
                    "minionsKilled": 109,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 13934,
                        "y": 9438
                    },
                    "currentGold": 1751,
                    "totalGold": 7531,
                    "level": 10,
                    "xp": 6761,
                    "minionsKilled": 25,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 14002,
                        "y": 10498
                    },
                    "currentGold": 970,
                    "totalGold": 5870,
                    "level": 11,
                    "xp": 7694,
                    "minionsKilled": 75,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 12708,
                        "y": 7238
                    },
                    "currentGold": 200,
                    "totalGold": 5108,
                    "level": 9,
                    "xp": 6042,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 61,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 13377,
                        "y": 7325
                    },
                    "currentGold": 1211,
                    "totalGold": 6611,
                    "level": 13,
                    "xp": 10434,
                    "minionsKilled": 137,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 14031,
                        "y": 9760
                    },
                    "currentGold": 924,
                    "totalGold": 8514,
                    "level": 11,
                    "xp": 7547,
                    "minionsKilled": 128,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 13471,
                        "y": 8390
                    },
                    "currentGold": 79,
                    "totalGold": 5503,
                    "level": 10,
                    "xp": 6521,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1084064,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1087237,
                    "participantId": 4,
                    "itemId": 3513
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1099261,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1106364,
                    "position": {
                        "x": 12754,
                        "y": 7449
                    },
                    "killerId": 7,
                    "victimId": 2,
                    "assistingParticipantIds": []
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1107289,
                    "participantId": 1,
                    "itemId": 2420
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1108114,
                    "position": {
                        "x": 13327,
                        "y": 8226
                    },
                    "killerId": 0,
                    "assistingParticipantIds": [
                        2
                    ],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "BOT_LANE",
                    "towerType": "INNER_TURRET"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1110029,
                    "position": {
                        "x": 12708,
                        "y": 7238
                    },
                    "killerId": 5,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        4,
                        2,
                        3
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1110426,
                    "position": {
                        "x": 9108,
                        "y": 8363
                    },
                    "killerId": 6,
                    "victimId": 1,
                    "assistingParticipantIds": []
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1111549,
                    "participantId": 6,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1115082,
                    "position": {
                        "x": 13471,
                        "y": 8390
                    },
                    "killerId": 4,
                    "victimId": 7,
                    "assistingParticipantIds": [
                        3
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1115413,
                    "position": {
                        "x": 13504,
                        "y": 8135
                    },
                    "killerId": 8,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1116701,
                    "participantId": 4,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1117396,
                    "participantId": 3,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1118354,
                    "participantId": 4,
                    "itemId": 3134
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1118354,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1119344,
                    "participantId": 4,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1120830,
                    "participantId": 2,
                    "itemId": 3086
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1120830,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1120897,
                    "participantId": 1,
                    "itemId": 3108
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1121260,
                    "position": {
                        "x": 14031,
                        "y": 9760
                    },
                    "killerId": 5,
                    "victimId": 8,
                    "assistingParticipantIds": [
                        4,
                        3
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1124760,
                    "participantId": 1,
                    "itemId": 3157
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1124760,
                    "participantId": 1,
                    "itemId": 3191
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1124760,
                    "participantId": 1,
                    "itemId": 3108
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1124760,
                    "participantId": 1,
                    "itemId": 2421
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1125124,
                    "position": {
                        "x": 13934,
                        "y": 9438
                    },
                    "killerId": 9,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        8,
                        7
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1127237,
                    "participantId": 8,
                    "itemId": 6691
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1127237,
                    "participantId": 8,
                    "itemId": 3134
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1127237,
                    "participantId": 8,
                    "itemId": 1036
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1127568,
                    "position": {
                        "x": 14002,
                        "y": 10498
                    },
                    "killerId": 5,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        3
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1128459,
                    "position": {
                        "x": 13985,
                        "y": 10044
                    },
                    "killerId": 9,
                    "victimId": 5,
                    "assistingParticipantIds": [
                        8
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1129549,
                    "participantId": 9,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1129714,
                    "participantId": 8,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1130705,
                    "participantId": 2,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1131101,
                    "participantId": 7,
                    "itemId": 6655
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1131101,
                    "participantId": 7,
                    "itemId": 3802
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1131200,
                    "participantId": 5,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1136552,
                    "participantId": 9,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1136552,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 1138799,
                    "participantId": 9,
                    "afterId": 0,
                    "beforeId": 3133
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 1139955,
                    "participantId": 3,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 1140194,
                    "participantId": 3,
                    "itemId": 2031
                }
            ],
            "timestamp": 1140326
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 8048,
                        "y": 7035
                    },
                    "currentGold": 478,
                    "totalGold": 9803,
                    "level": 13,
                    "xp": 10068,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 11424,
                        "y": 6087
                    },
                    "currentGold": 327,
                    "totalGold": 7252,
                    "level": 10,
                    "xp": 6570,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 84,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8099,
                        "y": 7128
                    },
                    "currentGold": 203,
                    "totalGold": 8013,
                    "level": 12,
                    "xp": 9845,
                    "minionsKilled": 127,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 11492,
                        "y": 5900
                    },
                    "currentGold": 579,
                    "totalGold": 7279,
                    "level": 10,
                    "xp": 6538,
                    "minionsKilled": 109,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 8141,
                        "y": 6933
                    },
                    "currentGold": 991,
                    "totalGold": 7671,
                    "level": 10,
                    "xp": 6761,
                    "minionsKilled": 25,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 10086,
                        "y": 8610
                    },
                    "currentGold": 516,
                    "totalGold": 6166,
                    "level": 11,
                    "xp": 7997,
                    "minionsKilled": 81,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 9434,
                        "y": 8998
                    },
                    "currentGold": 408,
                    "totalGold": 5316,
                    "level": 10,
                    "xp": 6231,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 65,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 13198,
                        "y": 6013
                    },
                    "currentGold": 1867,
                    "totalGold": 7267,
                    "level": 13,
                    "xp": 11376,
                    "minionsKilled": 149,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 3497,
                        "y": 13269
                    },
                    "currentGold": 568,
                    "totalGold": 9033,
                    "level": 11,
                    "xp": 8363,
                    "minionsKilled": 143,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 10525,
                        "y": 8832
                    },
                    "currentGold": 244,
                    "totalGold": 5669,
                    "level": 10,
                    "xp": 6521,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1140855,
                    "participantId": 3,
                    "itemId": 1018
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1141088,
                    "participantId": 3,
                    "itemId": 1042
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1142544,
                    "participantId": 7,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1142776,
                    "participantId": 8,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1143668,
                    "participantId": 5,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1144164,
                    "participantId": 5,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1144329,
                    "participantId": 8,
                    "itemId": 3363
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1144329,
                    "participantId": 8,
                    "itemId": 3340
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1151794,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 6
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1166362,
                    "participantId": 9,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1166362,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1166924,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1167320,
                    "participantId": 10,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1171549,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1177461,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1183044,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1185492,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 1192600,
                    "position": {
                        "x": 9866,
                        "y": 4414
                    },
                    "killerId": 7,
                    "monsterType": "DRAGON",
                    "monsterSubType": "AIR_DRAGON"
                }
            ],
            "timestamp": 1200328
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 5032,
                        "y": 10234
                    },
                    "currentGold": 677,
                    "totalGold": 10002,
                    "level": 13,
                    "xp": 10484,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 4611,
                        "y": 10006
                    },
                    "currentGold": 449,
                    "totalGold": 7374,
                    "level": 10,
                    "xp": 6616,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 84,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 4644,
                        "y": 9938
                    },
                    "currentGold": 603,
                    "totalGold": 8413,
                    "level": 13,
                    "xp": 10201,
                    "minionsKilled": 134,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 4174,
                        "y": 9933
                    },
                    "currentGold": 848,
                    "totalGold": 7548,
                    "level": 10,
                    "xp": 6837,
                    "minionsKilled": 113,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 4301,
                        "y": 9928
                    },
                    "currentGold": 1496,
                    "totalGold": 8176,
                    "level": 10,
                    "xp": 7151,
                    "minionsKilled": 26,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 8863,
                        "y": 8976
                    },
                    "currentGold": 80,
                    "totalGold": 6430,
                    "level": 11,
                    "xp": 8241,
                    "minionsKilled": 86,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 6063,
                        "y": 9970
                    },
                    "currentGold": 190,
                    "totalGold": 5498,
                    "level": 10,
                    "xp": 6356,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 65,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 5824,
                        "y": 10556
                    },
                    "currentGold": 2186,
                    "totalGold": 7586,
                    "level": 14,
                    "xp": 11514,
                    "minionsKilled": 153,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 7732,
                        "y": 7381
                    },
                    "currentGold": 207,
                    "totalGold": 9346,
                    "level": 12,
                    "xp": 8811,
                    "minionsKilled": 151,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 6340,
                        "y": 10086
                    },
                    "currentGold": 462,
                    "totalGold": 5887,
                    "level": 10,
                    "xp": 6821,
                    "minionsKilled": 15,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1204127,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1207033,
                    "participantId": 1,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1210144,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1214438,
                    "participantId": 8,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1220746,
                    "participantId": 8,
                    "itemId": 3077
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1220746,
                    "participantId": 8,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1222001,
                    "participantId": 8,
                    "itemId": 1036
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1225765,
                    "position": {
                        "x": 10504,
                        "y": 1029
                    },
                    "killerId": 0,
                    "assistingParticipantIds": [],
                    "teamId": 100,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "BOT_LANE",
                    "towerType": "OUTER_TURRET"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1227483,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1229530,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1229530,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1232305,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1234914,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1234914,
                    "participantId": 2,
                    "itemId": 2055
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1236830,
                    "position": {
                        "x": 8863,
                        "y": 8976
                    },
                    "killerId": 3,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        1
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1237919,
                    "participantId": 6,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1240165,
                    "participantId": 9,
                    "itemId": 3057
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1241948,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1245416,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1248290,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 8
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1250965,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1254598,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 5
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1259617,
                    "wardType": "YELLOW_TRINKET",
                    "killerId": 10
                }
            ],
            "timestamp": 1260356
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 3120,
                        "y": 2607
                    },
                    "currentGold": 50,
                    "totalGold": 10124,
                    "level": 13,
                    "xp": 10548,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 3630,
                        "y": 8840
                    },
                    "currentGold": 831,
                    "totalGold": 7756,
                    "level": 10,
                    "xp": 7183,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 92,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 3755,
                        "y": 9294
                    },
                    "currentGold": 729,
                    "totalGold": 8539,
                    "level": 13,
                    "xp": 10280,
                    "minionsKilled": 134,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 2731,
                        "y": 3398
                    },
                    "currentGold": 780,
                    "totalGold": 7780,
                    "level": 10,
                    "xp": 6966,
                    "minionsKilled": 114,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 1510,
                        "y": 645
                    },
                    "currentGold": 144,
                    "totalGold": 8624,
                    "level": 10,
                    "xp": 7281,
                    "minionsKilled": 26,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 5177,
                        "y": 10477
                    },
                    "currentGold": 527,
                    "totalGold": 6877,
                    "level": 12,
                    "xp": 9052,
                    "minionsKilled": 86,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 13210,
                        "y": 12519
                    },
                    "currentGold": 358,
                    "totalGold": 6541,
                    "level": 11,
                    "xp": 7879,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 65,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 5946,
                        "y": 9466
                    },
                    "currentGold": 2884,
                    "totalGold": 8284,
                    "level": 15,
                    "xp": 13068,
                    "minionsKilled": 153,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 4824,
                        "y": 10887
                    },
                    "currentGold": 1622,
                    "totalGold": 10762,
                    "level": 13,
                    "xp": 10183,
                    "minionsKilled": 156,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 6190,
                        "y": 10264
                    },
                    "currentGold": 1203,
                    "totalGold": 6628,
                    "level": 11,
                    "xp": 8530,
                    "minionsKilled": 15,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1261216,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1261216,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1262735,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 5
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1270431,
                    "position": {
                        "x": 5091,
                        "y": 10397
                    },
                    "killerId": 10,
                    "victimId": 5,
                    "assistingParticipantIds": [
                        6,
                        7
                    ]
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1271388,
                    "wardType": "CONTROL_WARD",
                    "killerId": 2
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1275947,
                    "position": {
                        "x": 4363,
                        "y": 10129
                    },
                    "killerId": 3,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        4,
                        2
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1276475,
                    "position": {
                        "x": 4497,
                        "y": 10170
                    },
                    "killerId": 8,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        10
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1283215,
                    "position": {
                        "x": 3875,
                        "y": 9674
                    },
                    "killerId": 8,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1284932,
                    "position": {
                        "x": 3755,
                        "y": 9294
                    },
                    "killerId": 8,
                    "victimId": 1,
                    "assistingParticipantIds": [
                        6,
                        7
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1287907,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1288601,
                    "participantId": 3,
                    "itemId": 3124
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1288601,
                    "participantId": 3,
                    "itemId": 6677
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1288601,
                    "participantId": 3,
                    "itemId": 1018
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1288601,
                    "participantId": 3,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1292863,
                    "participantId": 3,
                    "itemId": 2015
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1298115,
                    "wardType": "CONTROL_WARD",
                    "killerId": 8
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1300595,
                    "participantId": 7,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1302809,
                    "participantId": 10,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1302809,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 1307597,
                    "participantId": 10,
                    "afterId": 0,
                    "beforeId": 3044
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1308786,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1313576,
                    "participantId": 5,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1313576,
                    "participantId": 5,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1315095,
                    "participantId": 10,
                    "itemId": 3047
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1315095,
                    "participantId": 10,
                    "itemId": 1001
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1317307,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 1318298,
                    "position": {
                        "x": 5007,
                        "y": 10471
                    },
                    "killerId": 9,
                    "monsterType": "BARON_NASHOR"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1319586,
                    "participantId": 6,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1319817,
                    "participantId": 10,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 1320379
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 2849,
                        "y": 11220
                    },
                    "currentGold": 322,
                    "totalGold": 10397,
                    "level": 13,
                    "xp": 11116,
                    "minionsKilled": 115,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 5954,
                        "y": 5486
                    },
                    "currentGold": 229,
                    "totalGold": 8179,
                    "level": 11,
                    "xp": 8044,
                    "minionsKilled": 10,
                    "jungleMinionsKilled": 92,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 13670,
                        "y": 4820
                    },
                    "currentGold": 1075,
                    "totalGold": 8884,
                    "level": 13,
                    "xp": 10764,
                    "minionsKilled": 143,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 5347,
                        "y": 4913
                    },
                    "currentGold": 121,
                    "totalGold": 8071,
                    "level": 11,
                    "xp": 7452,
                    "minionsKilled": 124,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 10924,
                        "y": 5061
                    },
                    "currentGold": 356,
                    "totalGold": 8835,
                    "level": 11,
                    "xp": 7491,
                    "minionsKilled": 30,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 14027,
                        "y": 13841
                    },
                    "currentGold": 149,
                    "totalGold": 7099,
                    "level": 12,
                    "xp": 9201,
                    "minionsKilled": 86,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 10870,
                        "y": 7641
                    },
                    "currentGold": 651,
                    "totalGold": 6834,
                    "level": 11,
                    "xp": 8308,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 73,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 12106,
                        "y": 7611
                    },
                    "currentGold": 421,
                    "totalGold": 8421,
                    "level": 15,
                    "xp": 13219,
                    "minionsKilled": 154,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 7467,
                        "y": 7335
                    },
                    "currentGold": 322,
                    "totalGold": 11212,
                    "level": 13,
                    "xp": 10975,
                    "minionsKilled": 171,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 8806,
                        "y": 7759
                    },
                    "currentGold": 208,
                    "totalGold": 6783,
                    "level": 12,
                    "xp": 8655,
                    "minionsKilled": 16,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1321270,
                    "participantId": 8,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1324242,
                    "participantId": 9,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1326655,
                    "participantId": 7,
                    "itemId": 3191
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1328307,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1328604,
                    "participantId": 7,
                    "itemId": 2003
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 1330290,
                    "participantId": 7,
                    "afterId": 0,
                    "beforeId": 2003
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 1330455,
                    "participantId": 7,
                    "afterId": 0,
                    "beforeId": 2003
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1331644,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1331941,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1339308,
                    "position": {
                        "x": 8039,
                        "y": 10453
                    },
                    "killerId": 4,
                    "victimId": 9,
                    "assistingParticipantIds": []
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1340959,
                    "participantId": 4,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1341619,
                    "participantId": 8,
                    "itemId": 3074
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1341619,
                    "participantId": 8,
                    "itemId": 3077
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1341619,
                    "participantId": 8,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1342379,
                    "participantId": 6,
                    "itemId": 3157
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1342941,
                    "participantId": 9,
                    "itemId": 1018
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1345584,
                    "participantId": 3,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1352623,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1355068,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1355432,
                    "participantId": 4,
                    "itemId": 6676
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1355432,
                    "participantId": 4,
                    "itemId": 3134
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1355432,
                    "participantId": 4,
                    "itemId": 1037
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1355729,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1357084,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1357414,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1363624,
                    "participantId": 7,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1365374,
                    "participantId": 2,
                    "itemId": 3085
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1365374,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1365374,
                    "participantId": 2,
                    "itemId": 3086
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1365374,
                    "participantId": 2,
                    "itemId": 1042
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1367058,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1372639,
                    "participantId": 2,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1377330,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                }
            ],
            "timestamp": 1380411
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 6246,
                        "y": 6294
                    },
                    "currentGold": 633,
                    "totalGold": 10708,
                    "level": 14,
                    "xp": 11558,
                    "minionsKilled": 122,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 9938,
                        "y": 6622
                    },
                    "currentGold": 393,
                    "totalGold": 8343,
                    "level": 11,
                    "xp": 8229,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 92,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6822,
                        "y": 6502
                    },
                    "currentGold": 1300,
                    "totalGold": 9110,
                    "level": 13,
                    "xp": 11100,
                    "minionsKilled": 148,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 6172,
                        "y": 6464
                    },
                    "currentGold": 431,
                    "totalGold": 8381,
                    "level": 11,
                    "xp": 7753,
                    "minionsKilled": 131,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 6488,
                        "y": 6883
                    },
                    "currentGold": 548,
                    "totalGold": 9028,
                    "level": 11,
                    "xp": 7679,
                    "minionsKilled": 32,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 7781,
                        "y": 6686
                    },
                    "currentGold": 272,
                    "totalGold": 7222,
                    "level": 12,
                    "xp": 9338,
                    "minionsKilled": 86,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 7483,
                        "y": 7519
                    },
                    "currentGold": 868,
                    "totalGold": 7051,
                    "level": 12,
                    "xp": 8670,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 73,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8079,
                        "y": 7008
                    },
                    "currentGold": 813,
                    "totalGold": 8813,
                    "level": 15,
                    "xp": 13828,
                    "minionsKilled": 162,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 8081,
                        "y": 6914
                    },
                    "currentGold": 1153,
                    "totalGold": 12042,
                    "level": 14,
                    "xp": 11510,
                    "minionsKilled": 182,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 7746,
                        "y": 7657
                    },
                    "currentGold": 392,
                    "totalGold": 6966,
                    "level": 12,
                    "xp": 8734,
                    "minionsKilled": 19,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1384573,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1384573,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1385762,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1387582,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1392014,
                    "participantId": 5,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1393963,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1397465,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 1
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1399479,
                    "wardType": "CONTROL_WARD",
                    "killerId": 1
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1400932,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1404666,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1404666,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1407408,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1410912,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 5
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1419465,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1423824,
                    "position": {
                        "x": 9938,
                        "y": 6622
                    },
                    "killerId": 8,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        10,
                        6
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1425013,
                    "participantId": 10,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1425311,
                    "participantId": 8,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 1440439
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 8274,
                        "y": 6614
                    },
                    "currentGold": 791,
                    "totalGold": 10865,
                    "level": 14,
                    "xp": 11843,
                    "minionsKilled": 124,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 8713,
                        "y": 6029
                    },
                    "currentGold": 516,
                    "totalGold": 8466,
                    "level": 11,
                    "xp": 8229,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 92,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8636,
                        "y": 6751
                    },
                    "currentGold": 1436,
                    "totalGold": 9246,
                    "level": 13,
                    "xp": 11373,
                    "minionsKilled": 149,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 8004,
                        "y": 7244
                    },
                    "currentGold": 810,
                    "totalGold": 8760,
                    "level": 11,
                    "xp": 8098,
                    "minionsKilled": 141,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 8058,
                        "y": 7201
                    },
                    "currentGold": 779,
                    "totalGold": 9259,
                    "level": 11,
                    "xp": 8026,
                    "minionsKilled": 34,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 9822,
                        "y": 6496
                    },
                    "currentGold": 394,
                    "totalGold": 7344,
                    "level": 12,
                    "xp": 9451,
                    "minionsKilled": 86,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 9722,
                        "y": 6408
                    },
                    "currentGold": 991,
                    "totalGold": 7174,
                    "level": 12,
                    "xp": 8783,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 73,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 9672,
                        "y": 6405
                    },
                    "currentGold": 1035,
                    "totalGold": 9035,
                    "level": 15,
                    "xp": 13976,
                    "minionsKilled": 162,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 9775,
                        "y": 6406
                    },
                    "currentGold": 1456,
                    "totalGold": 12346,
                    "level": 14,
                    "xp": 11624,
                    "minionsKilled": 188,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 9974,
                        "y": 6839
                    },
                    "currentGold": 546,
                    "totalGold": 7121,
                    "level": 12,
                    "xp": 8847,
                    "minionsKilled": 20,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1446779,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1446779,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1491307,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                }
            ],
            "timestamp": 1500463
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 9250,
                        "y": 6165
                    },
                    "currentGold": 14,
                    "totalGold": 11384,
                    "level": 14,
                    "xp": 12072,
                    "minionsKilled": 124,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 7513,
                        "y": 1277
                    },
                    "currentGold": 115,
                    "totalGold": 8665,
                    "level": 12,
                    "xp": 8661,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 92,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6490,
                        "y": 1153
                    },
                    "currentGold": 380,
                    "totalGold": 9439,
                    "level": 14,
                    "xp": 11512,
                    "minionsKilled": 150,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 4501,
                        "y": 4365
                    },
                    "currentGold": 986,
                    "totalGold": 8936,
                    "level": 11,
                    "xp": 8420,
                    "minionsKilled": 141,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 3279,
                        "y": 2220
                    },
                    "currentGold": 291,
                    "totalGold": 9821,
                    "level": 11,
                    "xp": 8349,
                    "minionsKilled": 35,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 8151,
                        "y": 1274
                    },
                    "currentGold": 1318,
                    "totalGold": 8268,
                    "level": 13,
                    "xp": 11035,
                    "minionsKilled": 97,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 9567,
                        "y": 10156
                    },
                    "currentGold": 808,
                    "totalGold": 7691,
                    "level": 12,
                    "xp": 9358,
                    "minionsKilled": 13,
                    "jungleMinionsKilled": 73,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7159,
                        "y": 6065
                    },
                    "currentGold": 1483,
                    "totalGold": 9483,
                    "level": 16,
                    "xp": 14893,
                    "minionsKilled": 162,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 6653,
                        "y": 7677
                    },
                    "currentGold": 2995,
                    "totalGold": 13885,
                    "level": 14,
                    "xp": 12679,
                    "minionsKilled": 197,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 12116,
                        "y": 11836
                    },
                    "currentGold": 205,
                    "totalGold": 7680,
                    "level": 12,
                    "xp": 9675,
                    "minionsKilled": 20,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1502479,
                    "position": {
                        "x": 9011,
                        "y": 6494
                    },
                    "killerId": 10,
                    "victimId": 1,
                    "assistingParticipantIds": [
                        8,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1505979,
                    "position": {
                        "x": 9305,
                        "y": 6367
                    },
                    "killerId": 3,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        5,
                        1,
                        2
                    ]
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1507003,
                    "wardType": "SIGHT_WARD",
                    "killerId": 3
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1507135,
                    "position": {
                        "x": 10092,
                        "y": 6340
                    },
                    "killerId": 9,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        6,
                        8,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1510505,
                    "position": {
                        "x": 9176,
                        "y": 5715
                    },
                    "killerId": 8,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        10,
                        6,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1512816,
                    "position": {
                        "x": 9253,
                        "y": 6325
                    },
                    "killerId": 5,
                    "victimId": 7,
                    "assistingParticipantIds": [
                        4,
                        3
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1515624,
                    "position": {
                        "x": 8263,
                        "y": 6238
                    },
                    "killerId": 8,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1518728,
                    "position": {
                        "x": 9250,
                        "y": 6165
                    },
                    "killerId": 8,
                    "victimId": 5,
                    "assistingParticipantIds": [
                        9,
                        6,
                        7
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1520908,
                    "participantId": 1,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1523023,
                    "participantId": 9,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1523056,
                    "participantId": 3,
                    "itemId": 3086
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1523353,
                    "participantId": 7,
                    "itemId": 3108
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1524278,
                    "wardType": "CONTROL_WARD",
                    "killerId": 9
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1525831,
                    "participantId": 4,
                    "itemId": 1018
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1526294,
                    "participantId": 10,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1526294,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 1532503,
                    "position": {
                        "x": 9866,
                        "y": 4414
                    },
                    "killerId": 9,
                    "monsterType": "DRAGON",
                    "monsterSubType": "AIR_DRAGON"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1534650,
                    "participantId": 1,
                    "itemId": 4630
                },
                {
                    "type": "ITEM_UNDO",
                    "timestamp": 1536666,
                    "participantId": 1,
                    "afterId": 0,
                    "beforeId": 4630
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1537988,
                    "participantId": 1,
                    "itemId": 1058
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1545221,
                    "position": {
                        "x": 5846,
                        "y": 6396
                    },
                    "killerId": 6,
                    "assistingParticipantIds": [
                        8
                    ],
                    "teamId": 100,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "MID_LANE",
                    "towerType": "OUTER_TURRET"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1549714,
                    "participantId": 6,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 1551432,
                    "participantId": 5,
                    "itemId": 1055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1552060,
                    "participantId": 5,
                    "itemId": 3071
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1552060,
                    "participantId": 5,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1552060,
                    "participantId": 5,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1555164,
                    "participantId": 5,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1559030,
                    "participantId": 4,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                }
            ],
            "timestamp": 1560483
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 6388,
                        "y": 8224
                    },
                    "currentGold": 473,
                    "totalGold": 11842,
                    "level": 14,
                    "xp": 12716,
                    "minionsKilled": 135,
                    "jungleMinionsKilled": 20,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 8189,
                        "y": 6996
                    },
                    "currentGold": 766,
                    "totalGold": 9316,
                    "level": 12,
                    "xp": 9635,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 100,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8022,
                        "y": 5793
                    },
                    "currentGold": 1035,
                    "totalGold": 10095,
                    "level": 14,
                    "xp": 12745,
                    "minionsKilled": 164,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 6018,
                        "y": 6086
                    },
                    "currentGold": 1857,
                    "totalGold": 9807,
                    "level": 12,
                    "xp": 9562,
                    "minionsKilled": 153,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 5742,
                        "y": 5995
                    },
                    "currentGold": 680,
                    "totalGold": 10210,
                    "level": 12,
                    "xp": 9203,
                    "minionsKilled": 37,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 10936,
                        "y": 10560
                    },
                    "currentGold": 190,
                    "totalGold": 8390,
                    "level": 13,
                    "xp": 11035,
                    "minionsKilled": 97,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 6468,
                        "y": 6355
                    },
                    "currentGold": 1152,
                    "totalGold": 8035,
                    "level": 12,
                    "xp": 9953,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 81,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7293,
                        "y": 8511
                    },
                    "currentGold": 590,
                    "totalGold": 10080,
                    "level": 16,
                    "xp": 15234,
                    "minionsKilled": 163,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 7557,
                        "y": 7380
                    },
                    "currentGold": 1034,
                    "totalGold": 14293,
                    "level": 15,
                    "xp": 13121,
                    "minionsKilled": 204,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 8302,
                        "y": 8138
                    },
                    "currentGold": 462,
                    "totalGold": 7937,
                    "level": 13,
                    "xp": 10083,
                    "minionsKilled": 23,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_KILL",
                    "timestamp": 1564480,
                    "wardType": "CONTROL_WARD",
                    "killerId": 8
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1565603,
                    "position": {
                        "x": 9112,
                        "y": 1370
                    },
                    "killerId": 4,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        1
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1567882,
                    "participantId": 9,
                    "itemId": 3508
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1567882,
                    "participantId": 9,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1567882,
                    "participantId": 9,
                    "itemId": 3057
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1567882,
                    "participantId": 9,
                    "itemId": 1018
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1568180,
                    "participantId": 6,
                    "itemId": 3916
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 1569963,
                    "participantId": 6,
                    "itemId": 1056
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1570789,
                    "participantId": 6,
                    "itemId": 1026
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1574521,
                    "participantId": 3,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1574918,
                    "participantId": 2,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1578847,
                    "participantId": 8,
                    "itemId": 3035
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1579013,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1579409,
                    "participantId": 9,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 1579970,
                    "participantId": 8,
                    "itemId": 1055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1580566,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1580698,
                    "participantId": 8,
                    "itemId": 3133
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1583903,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1598008,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1599329,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1607618,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1609963,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1614126,
                    "position": {
                        "x": 8189,
                        "y": 6996
                    },
                    "killerId": 6,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        8,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1614258,
                    "position": {
                        "x": 6468,
                        "y": 6355
                    },
                    "killerId": 2,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        3
                    ]
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1616901,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1620105,
                    "participantId": 8,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1620204,
                    "wardType": "CONTROL_WARD",
                    "killerId": 5
                }
            ],
            "timestamp": 1620508
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 3673,
                        "y": 10598
                    },
                    "currentGold": 742,
                    "totalGold": 12111,
                    "level": 15,
                    "xp": 13042,
                    "minionsKilled": 136,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 3653,
                        "y": 6524
                    },
                    "currentGold": 959,
                    "totalGold": 9509,
                    "level": 12,
                    "xp": 9795,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 103,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 1731,
                        "y": 2648
                    },
                    "currentGold": 204,
                    "totalGold": 10313,
                    "level": 14,
                    "xp": 12965,
                    "minionsKilled": 165,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 600,
                        "y": 805
                    },
                    "currentGold": 51,
                    "totalGold": 10175,
                    "level": 12,
                    "xp": 9820,
                    "minionsKilled": 163,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 3166,
                        "y": 2682
                    },
                    "currentGold": 66,
                    "totalGold": 10420,
                    "level": 12,
                    "xp": 9460,
                    "minionsKilled": 38,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 7277,
                        "y": 13986
                    },
                    "currentGold": 632,
                    "totalGold": 8832,
                    "level": 14,
                    "xp": 11610,
                    "minionsKilled": 108,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 10029,
                        "y": 8718
                    },
                    "currentGold": 399,
                    "totalGold": 8157,
                    "level": 12,
                    "xp": 9953,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 81,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 6893,
                        "y": 9971
                    },
                    "currentGold": 755,
                    "totalGold": 10244,
                    "level": 16,
                    "xp": 15423,
                    "minionsKilled": 165,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 12802,
                        "y": 12604
                    },
                    "currentGold": 470,
                    "totalGold": 14654,
                    "level": 15,
                    "xp": 13440,
                    "minionsKilled": 208,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 14340,
                        "y": 14391
                    },
                    "currentGold": 617,
                    "totalGold": 8091,
                    "level": 13,
                    "xp": 10178,
                    "minionsKilled": 24,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1620938,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1623811,
                    "participantId": 7,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1627047,
                    "participantId": 10,
                    "itemId": 1037
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1629228,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 5
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1660508,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1669261,
                    "participantId": 8,
                    "itemId": 6694
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1669261,
                    "participantId": 8,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1669261,
                    "participantId": 8,
                    "itemId": 3035
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1672795,
                    "participantId": 9,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1673358,
                    "participantId": 3,
                    "itemId": 3094
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1673358,
                    "participantId": 3,
                    "itemId": 3086
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1673358,
                    "participantId": 3,
                    "itemId": 2015
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1673985,
                    "participantId": 3,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 1675340,
                    "participantId": 1,
                    "itemId": 2033
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1675703,
                    "participantId": 8,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1676364,
                    "participantId": 1,
                    "itemId": 1058
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1677850,
                    "participantId": 5,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1679171,
                    "participantId": 2,
                    "itemId": 1038
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1679666,
                    "participantId": 2,
                    "itemId": 1037
                }
            ],
            "timestamp": 1680525
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 8122,
                        "y": 10210
                    },
                    "currentGold": 1141,
                    "totalGold": 12511,
                    "level": 15,
                    "xp": 13533,
                    "minionsKilled": 147,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 7984,
                        "y": 9305
                    },
                    "currentGold": 1181,
                    "totalGold": 9731,
                    "level": 13,
                    "xp": 10109,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 108,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8275,
                        "y": 8103
                    },
                    "currentGold": 500,
                    "totalGold": 10609,
                    "level": 15,
                    "xp": 13286,
                    "minionsKilled": 168,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 7808,
                        "y": 8375
                    },
                    "currentGold": 347,
                    "totalGold": 10472,
                    "level": 13,
                    "xp": 10240,
                    "minionsKilled": 169,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 7777,
                        "y": 8323
                    },
                    "currentGold": 465,
                    "totalGold": 10820,
                    "level": 13,
                    "xp": 10085,
                    "minionsKilled": 44,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 9169,
                        "y": 9946
                    },
                    "currentGold": 473,
                    "totalGold": 9023,
                    "level": 14,
                    "xp": 11830,
                    "minionsKilled": 110,
                    "jungleMinionsKilled": 18,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 9450,
                        "y": 9029
                    },
                    "currentGold": 607,
                    "totalGold": 8365,
                    "level": 13,
                    "xp": 10182,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 9227,
                        "y": 9683
                    },
                    "currentGold": 1044,
                    "totalGold": 10534,
                    "level": 16,
                    "xp": 15596,
                    "minionsKilled": 168,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 9208,
                        "y": 8974
                    },
                    "currentGold": 759,
                    "totalGold": 14944,
                    "level": 15,
                    "xp": 13786,
                    "minionsKilled": 214,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 9055,
                        "y": 9936
                    },
                    "currentGold": 185,
                    "totalGold": 8260,
                    "level": 13,
                    "xp": 10341,
                    "minionsKilled": 26,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1680624,
                    "participantId": 7,
                    "itemId": 3157
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1680624,
                    "participantId": 7,
                    "itemId": 3191
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1680624,
                    "participantId": 7,
                    "itemId": 3108
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1680624,
                    "participantId": 7,
                    "itemId": 2424
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1684093,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1684357,
                    "participantId": 7,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1686042,
                    "participantId": 9,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1686042,
                    "participantId": 9,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1686042,
                    "participantId": 9,
                    "itemId": 1036
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1694431,
                    "participantId": 10,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1695554,
                    "participantId": 1,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1700772,
                    "participantId": 4,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1702291,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1702753,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 8
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1702753,
                    "participantId": 8,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1703909,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 5
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1703909,
                    "participantId": 5,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1709030,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1711244,
                    "wardType": "CONTROL_WARD",
                    "killerId": 1
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1713192,
                    "participantId": 2,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1717386,
                    "wardType": "SIGHT_WARD",
                    "killerId": 1
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1721615,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1730241,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 5
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1736417,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 9
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1738036,
                    "wardType": "YELLOW_TRINKET",
                    "killerId": 5
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1739457,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 9
                }
            ],
            "timestamp": 1740528
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 8181,
                        "y": 7989
                    },
                    "currentGold": 1358,
                    "totalGold": 12727,
                    "level": 15,
                    "xp": 14183,
                    "minionsKilled": 148,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 8871,
                        "y": 8850
                    },
                    "currentGold": 2859,
                    "totalGold": 11408,
                    "level": 13,
                    "xp": 10932,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 108,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 8051,
                        "y": 7714
                    },
                    "currentGold": 744,
                    "totalGold": 10854,
                    "level": 15,
                    "xp": 13943,
                    "minionsKilled": 170,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 7482,
                        "y": 7865
                    },
                    "currentGold": 506,
                    "totalGold": 10631,
                    "level": 13,
                    "xp": 10263,
                    "minionsKilled": 171,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 5856,
                        "y": 7141
                    },
                    "currentGold": 783,
                    "totalGold": 11137,
                    "level": 13,
                    "xp": 10391,
                    "minionsKilled": 44,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 8126,
                        "y": 8072
                    },
                    "currentGold": 596,
                    "totalGold": 9146,
                    "level": 14,
                    "xp": 11921,
                    "minionsKilled": 110,
                    "jungleMinionsKilled": 18,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 8393,
                        "y": 8153
                    },
                    "currentGold": 730,
                    "totalGold": 8488,
                    "level": 13,
                    "xp": 10519,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8696,
                        "y": 8874
                    },
                    "currentGold": 1202,
                    "totalGold": 10692,
                    "level": 16,
                    "xp": 15687,
                    "minionsKilled": 170,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 7424,
                        "y": 6166
                    },
                    "currentGold": 1524,
                    "totalGold": 15708,
                    "level": 15,
                    "xp": 14383,
                    "minionsKilled": 225,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 9307,
                        "y": 8642
                    },
                    "currentGold": 477,
                    "totalGold": 8551,
                    "level": 13,
                    "xp": 10679,
                    "minionsKilled": 26,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1743699,
                    "participantId": 3,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1751365,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1754144,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1761220,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 2
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1762379,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1762676,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 3
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1762676,
                    "participantId": 3,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1780174,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1786855,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1788013,
                    "position": {
                        "x": 5856,
                        "y": 7141
                    },
                    "killerId": 8,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1791482,
                    "position": {
                        "x": 7424,
                        "y": 6166
                    },
                    "killerId": 4,
                    "victimId": 8,
                    "assistingParticipantIds": [
                        3
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1799617,
                    "position": {
                        "x": 8696,
                        "y": 8874
                    },
                    "killerId": 4,
                    "victimId": 6,
                    "assistingParticipantIds": [
                        5,
                        1
                    ]
                }
            ],
            "timestamp": 1800543
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 9979,
                        "y": 4432
                    },
                    "currentGold": 2373,
                    "totalGold": 13742,
                    "level": 16,
                    "xp": 14916,
                    "minionsKilled": 152,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 5519,
                        "y": 1027
                    },
                    "currentGold": 256,
                    "totalGold": 11956,
                    "level": 13,
                    "xp": 11168,
                    "minionsKilled": 12,
                    "jungleMinionsKilled": 108,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 1072,
                        "y": 422
                    },
                    "currentGold": 285,
                    "totalGold": 11195,
                    "level": 15,
                    "xp": 14274,
                    "minionsKilled": 170,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 10185,
                        "y": 4786
                    },
                    "currentGold": 1086,
                    "totalGold": 11211,
                    "level": 13,
                    "xp": 11179,
                    "minionsKilled": 175,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 6111,
                        "y": 7162
                    },
                    "currentGold": 123,
                    "totalGold": 11378,
                    "level": 13,
                    "xp": 10391,
                    "minionsKilled": 44,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 11498,
                        "y": 6572
                    },
                    "currentGold": 572,
                    "totalGold": 9996,
                    "level": 15,
                    "xp": 13087,
                    "minionsKilled": 120,
                    "jungleMinionsKilled": 18,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 12187,
                        "y": 9886
                    },
                    "currentGold": 52,
                    "totalGold": 8610,
                    "level": 13,
                    "xp": 10803,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 10035,
                        "y": 7852
                    },
                    "currentGold": 450,
                    "totalGold": 11189,
                    "level": 16,
                    "xp": 16031,
                    "minionsKilled": 170,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 11828,
                        "y": 7259
                    },
                    "currentGold": 346,
                    "totalGold": 15830,
                    "level": 15,
                    "xp": 14383,
                    "minionsKilled": 225,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 12162,
                        "y": 9751
                    },
                    "currentGold": 332,
                    "totalGold": 8842,
                    "level": 13,
                    "xp": 11206,
                    "minionsKilled": 26,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1802632,
                    "position": {
                        "x": 7868,
                        "y": 7112
                    },
                    "killerId": 6,
                    "victimId": 1,
                    "assistingParticipantIds": [
                        9,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1803887,
                    "position": {
                        "x": 9638,
                        "y": 9079
                    },
                    "killerId": 4,
                    "victimId": 7,
                    "assistingParticipantIds": [
                        5,
                        1,
                        2
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1804152,
                    "position": {
                        "x": 8031,
                        "y": 7524
                    },
                    "killerId": 5,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        1,
                        2
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 1805639,
                    "position": {
                        "x": 9524,
                        "y": 9005
                    },
                    "killerId": 9,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        6,
                        7
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1808924,
                    "participantId": 4,
                    "itemId": 3031
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1808924,
                    "participantId": 4,
                    "itemId": 1018
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1811838,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1812698,
                    "participantId": 6,
                    "itemId": 3165
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1812698,
                    "participantId": 6,
                    "itemId": 1026
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1812698,
                    "participantId": 6,
                    "itemId": 3916
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1815574,
                    "participantId": 6,
                    "itemId": 1028
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1816568,
                    "position": {
                        "x": 9767,
                        "y": 10113
                    },
                    "killerId": 2,
                    "assistingParticipantIds": [
                        5,
                        1
                    ],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "MID_LANE",
                    "towerType": "INNER_TURRET"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1820698,
                    "participantId": 10,
                    "itemId": 3053
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1820698,
                    "participantId": 10,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1820698,
                    "participantId": 10,
                    "itemId": 3044
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1820698,
                    "participantId": 10,
                    "itemId": 1028
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1821393,
                    "participantId": 7,
                    "itemId": 1052
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1822648,
                    "participantId": 5,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1826617,
                    "participantId": 8,
                    "itemId": 1038
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1829063,
                    "participantId": 9,
                    "itemId": 1037
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1830153,
                    "position": {
                        "x": 11134,
                        "y": 11207
                    },
                    "killerId": 2,
                    "assistingParticipantIds": [
                        5
                    ],
                    "teamId": 200,
                    "buildingType": "TOWER_BUILDING",
                    "laneType": "MID_LANE",
                    "towerType": "BASE_TURRET"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1832503,
                    "participantId": 3,
                    "itemId": 1036
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1834916,
                    "participantId": 3,
                    "itemId": 1053
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1834916,
                    "participantId": 3,
                    "itemId": 1036
                },
                {
                    "type": "BUILDING_KILL",
                    "timestamp": 1835708,
                    "position": {
                        "x": 11598,
                        "y": 11667
                    },
                    "killerId": 0,
                    "assistingParticipantIds": [
                        5
                    ],
                    "teamId": 200,
                    "buildingType": "INHIBITOR_BUILDING",
                    "laneType": "MID_LANE",
                    "towerType": "UNDEFINED_TURRET"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1849121,
                    "participantId": 9,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1851236,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1860220,
                    "participantId": 1,
                    "itemId": 3916
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 1860499,
                    "position": {
                        "x": 9866,
                        "y": 4414
                    },
                    "killerId": 5,
                    "monsterType": "DRAGON",
                    "monsterSubType": "AIR_DRAGON"
                }
            ],
            "timestamp": 1860565
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 7617,
                        "y": 7202
                    },
                    "currentGold": 505,
                    "totalGold": 13924,
                    "level": 16,
                    "xp": 14982,
                    "minionsKilled": 153,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 5575,
                        "y": 9081
                    },
                    "currentGold": 684,
                    "totalGold": 12384,
                    "level": 14,
                    "xp": 12133,
                    "minionsKilled": 19,
                    "jungleMinionsKilled": 112,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7369,
                        "y": 7232
                    },
                    "currentGold": 471,
                    "totalGold": 11380,
                    "level": 15,
                    "xp": 14613,
                    "minionsKilled": 174,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 4859,
                        "y": 5169
                    },
                    "currentGold": 62,
                    "totalGold": 11486,
                    "level": 13,
                    "xp": 11405,
                    "minionsKilled": 179,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 6910,
                        "y": 7467
                    },
                    "currentGold": 353,
                    "totalGold": 11608,
                    "level": 13,
                    "xp": 10503,
                    "minionsKilled": 46,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 8532,
                        "y": 8580
                    },
                    "currentGold": 853,
                    "totalGold": 10278,
                    "level": 15,
                    "xp": 13387,
                    "minionsKilled": 125,
                    "jungleMinionsKilled": 22,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 8528,
                        "y": 9975
                    },
                    "currentGold": 175,
                    "totalGold": 8733,
                    "level": 13,
                    "xp": 10959,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 8733,
                        "y": 8065
                    },
                    "currentGold": 808,
                    "totalGold": 11548,
                    "level": 16,
                    "xp": 16272,
                    "minionsKilled": 175,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 8506,
                        "y": 8533
                    },
                    "currentGold": 737,
                    "totalGold": 16221,
                    "level": 16,
                    "xp": 14923,
                    "minionsKilled": 227,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 7389,
                        "y": 11130
                    },
                    "currentGold": 515,
                    "totalGold": 9025,
                    "level": 13,
                    "xp": 11363,
                    "minionsKilled": 29,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1864631,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1871205,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1871436,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1872360,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1872393,
                    "participantId": 4,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1872823,
                    "participantId": 5,
                    "itemId": 3211
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1873286,
                    "participantId": 5,
                    "itemId": 3067
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1874972,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 4
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1876525,
                    "participantId": 5,
                    "itemId": 3364
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1876525,
                    "participantId": 5,
                    "itemId": 3340
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1881844,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1882043,
                    "wardType": "CONTROL_WARD",
                    "creatorId": 10
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1882043,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1895089,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 6
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1895387,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1895882,
                    "participantId": 8,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1901401,
                    "wardType": "CONTROL_WARD",
                    "killerId": 3
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1903812,
                    "wardType": "SIGHT_WARD",
                    "killerId": 3
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1904439,
                    "participantId": 2,
                    "itemId": 3031
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1904439,
                    "participantId": 2,
                    "itemId": 1038
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1904439,
                    "participantId": 2,
                    "itemId": 1037
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1905100,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1906751,
                    "participantId": 2,
                    "itemId": 2055
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1907940,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 7
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1910152,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1912036,
                    "wardType": "SIGHT_WARD",
                    "killerId": 5
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1916364,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                }
            ],
            "timestamp": 1920591
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 6707,
                        "y": 6927
                    },
                    "currentGold": 635,
                    "totalGold": 14055,
                    "level": 16,
                    "xp": 15278,
                    "minionsKilled": 153,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 5144,
                        "y": 8458
                    },
                    "currentGold": 807,
                    "totalGold": 12506,
                    "level": 14,
                    "xp": 12133,
                    "minionsKilled": 19,
                    "jungleMinionsKilled": 112,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 6166,
                        "y": 8596
                    },
                    "currentGold": 627,
                    "totalGold": 11536,
                    "level": 16,
                    "xp": 14758,
                    "minionsKilled": 176,
                    "jungleMinionsKilled": 8,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 4952,
                        "y": 8460
                    },
                    "currentGold": 362,
                    "totalGold": 11787,
                    "level": 14,
                    "xp": 11550,
                    "minionsKilled": 185,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 6545,
                        "y": 6603
                    },
                    "currentGold": 567,
                    "totalGold": 11821,
                    "level": 13,
                    "xp": 10824,
                    "minionsKilled": 47,
                    "jungleMinionsKilled": 0,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 11103,
                        "y": 8489
                    },
                    "currentGold": 1060,
                    "totalGold": 10485,
                    "level": 15,
                    "xp": 13715,
                    "minionsKilled": 125,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 7261,
                        "y": 9979
                    },
                    "currentGold": 327,
                    "totalGold": 8885,
                    "level": 13,
                    "xp": 11155,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7930,
                        "y": 8156
                    },
                    "currentGold": 1379,
                    "totalGold": 12118,
                    "level": 17,
                    "xp": 16664,
                    "minionsKilled": 187,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 7835,
                        "y": 8286
                    },
                    "currentGold": 1013,
                    "totalGold": 16497,
                    "level": 16,
                    "xp": 15386,
                    "minionsKilled": 236,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 8016,
                        "y": 8533
                    },
                    "currentGold": 684,
                    "totalGold": 9194,
                    "level": 14,
                    "xp": 11521,
                    "minionsKilled": 31,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1923134,
                    "participantId": 1,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1930766,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1945074,
                    "wardType": "YELLOW_TRINKET",
                    "creatorId": 9
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1946727,
                    "participantId": 2,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1954532,
                    "participantId": 7,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1958102,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 6
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 1959426,
                    "participantId": 6,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1965240,
                    "wardType": "SIGHT_WARD",
                    "killerId": 6
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1967823,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                }
            ],
            "timestamp": 1980595
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 5027,
                        "y": 10463
                    },
                    "currentGold": 419,
                    "totalGold": 14688,
                    "level": 16,
                    "xp": 16437,
                    "minionsKilled": 157,
                    "jungleMinionsKilled": 28,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 5291,
                        "y": 10251
                    },
                    "currentGold": 517,
                    "totalGold": 12966,
                    "level": 15,
                    "xp": 13219,
                    "minionsKilled": 19,
                    "jungleMinionsKilled": 112,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 2074,
                        "y": 1250
                    },
                    "currentGold": 161,
                    "totalGold": 12371,
                    "level": 16,
                    "xp": 15932,
                    "minionsKilled": 176,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 3783,
                        "y": 9359
                    },
                    "currentGold": 875,
                    "totalGold": 12299,
                    "level": 14,
                    "xp": 12665,
                    "minionsKilled": 185,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 4003,
                        "y": 10225
                    },
                    "currentGold": 1479,
                    "totalGold": 12734,
                    "level": 14,
                    "xp": 12138,
                    "minionsKilled": 49,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 4743,
                        "y": 10132
                    },
                    "currentGold": 95,
                    "totalGold": 11445,
                    "level": 15,
                    "xp": 14416,
                    "minionsKilled": 125,
                    "jungleMinionsKilled": 30,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 5036,
                        "y": 10094
                    },
                    "currentGold": 207,
                    "totalGold": 9065,
                    "level": 14,
                    "xp": 11735,
                    "minionsKilled": 14,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 7960,
                        "y": 8724
                    },
                    "currentGold": 2356,
                    "totalGold": 13095,
                    "level": 17,
                    "xp": 17197,
                    "minionsKilled": 188,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 5978,
                        "y": 9192
                    },
                    "currentGold": 1824,
                    "totalGold": 17308,
                    "level": 16,
                    "xp": 16331,
                    "minionsKilled": 236,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 7318,
                        "y": 8875
                    },
                    "currentGold": 1087,
                    "totalGold": 9596,
                    "level": 14,
                    "xp": 12373,
                    "minionsKilled": 31,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1982616,
                    "participantId": 10,
                    "itemId": 1029
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 1991834,
                    "wardType": "YELLOW_TRINKET",
                    "killerId": 5
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 1998079,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 2
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 1999269,
                    "participantId": 9,
                    "itemId": 3053
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1999269,
                    "participantId": 9,
                    "itemId": 1037
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 1999269,
                    "participantId": 9,
                    "itemId": 3044
                },
                {
                    "type": "ELITE_MONSTER_KILL",
                    "timestamp": 2003834,
                    "position": {
                        "x": 5007,
                        "y": 10471
                    },
                    "killerId": 3,
                    "monsterType": "BARON_NASHOR"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2005357,
                    "participantId": 3,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2009951,
                    "position": {
                        "x": 5027,
                        "y": 10463
                    },
                    "killerId": 6,
                    "victimId": 5,
                    "assistingParticipantIds": [
                        9,
                        10,
                        8,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2010984,
                    "position": {
                        "x": 5291,
                        "y": 10251
                    },
                    "killerId": 9,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        6,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2012041,
                    "position": {
                        "x": 5036,
                        "y": 10094
                    },
                    "killerId": 1,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        5,
                        2,
                        3
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2013132,
                    "participantId": 10,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2013528,
                    "position": {
                        "x": 4743,
                        "y": 10132
                    },
                    "killerId": 3,
                    "victimId": 9,
                    "assistingParticipantIds": [
                        5,
                        4,
                        1,
                        2
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2014090,
                    "participantId": 4,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2014917,
                    "participantId": 4,
                    "itemId": 3133
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2014917,
                    "participantId": 4,
                    "itemId": 1036
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2020136,
                    "position": {
                        "x": 3783,
                        "y": 9359
                    },
                    "killerId": 8,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        9,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2025685,
                    "position": {
                        "x": 4003,
                        "y": 10225
                    },
                    "killerId": 6,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        8,
                        7
                    ]
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2030707,
                    "participantId": 5,
                    "itemId": 3065
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2030707,
                    "participantId": 5,
                    "itemId": 3211
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2030707,
                    "participantId": 5,
                    "itemId": 3067
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 2033977,
                    "wardType": "CONTROL_WARD",
                    "killerId": 6
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2036158,
                    "participantId": 9,
                    "itemId": 3067
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2036752,
                    "participantId": 1,
                    "itemId": 3089
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2036752,
                    "participantId": 1,
                    "itemId": 1058
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2036752,
                    "participantId": 1,
                    "itemId": 1058
                }
            ],
            "timestamp": 2040618
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "position": {
                        "x": 8028,
                        "y": 7616
                    },
                    "currentGold": 706,
                    "totalGold": 14975,
                    "level": 17,
                    "xp": 16690,
                    "minionsKilled": 158,
                    "jungleMinionsKilled": 32,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "2": {
                    "participantId": 4,
                    "position": {
                        "x": 9811,
                        "y": 6490
                    },
                    "currentGold": 654,
                    "totalGold": 13104,
                    "level": 15,
                    "xp": 13237,
                    "minionsKilled": 20,
                    "jungleMinionsKilled": 112,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "3": {
                    "participantId": 1,
                    "position": {
                        "x": 7810,
                        "y": 8477
                    },
                    "currentGold": 368,
                    "totalGold": 12577,
                    "level": 16,
                    "xp": 16374,
                    "minionsKilled": 181,
                    "jungleMinionsKilled": 12,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "4": {
                    "participantId": 2,
                    "position": {
                        "x": 7496,
                        "y": 7596
                    },
                    "currentGold": 777,
                    "totalGold": 12522,
                    "level": 14,
                    "xp": 12852,
                    "minionsKilled": 185,
                    "jungleMinionsKilled": 16,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "5": {
                    "participantId": 3,
                    "position": {
                        "x": 8448,
                        "y": 7928
                    },
                    "currentGold": 1705,
                    "totalGold": 12960,
                    "level": 14,
                    "xp": 12276,
                    "minionsKilled": 53,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "6": {
                    "participantId": 9,
                    "position": {
                        "x": 9174,
                        "y": 9157
                    },
                    "currentGold": 335,
                    "totalGold": 11684,
                    "level": 15,
                    "xp": 14644,
                    "minionsKilled": 128,
                    "jungleMinionsKilled": 34,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "7": {
                    "participantId": 10,
                    "position": {
                        "x": 8700,
                        "y": 10711
                    },
                    "currentGold": 275,
                    "totalGold": 9208,
                    "level": 14,
                    "xp": 11849,
                    "minionsKilled": 15,
                    "jungleMinionsKilled": 85,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "8": {
                    "participantId": 6,
                    "position": {
                        "x": 13389,
                        "y": 13813
                    },
                    "currentGold": 59,
                    "totalGold": 13399,
                    "level": 17,
                    "xp": 17681,
                    "minionsKilled": 194,
                    "jungleMinionsKilled": 26,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "9": {
                    "participantId": 8,
                    "position": {
                        "x": 9184,
                        "y": 8966
                    },
                    "currentGold": 266,
                    "totalGold": 17750,
                    "level": 17,
                    "xp": 16915,
                    "minionsKilled": 246,
                    "jungleMinionsKilled": 24,
                    "dominionScore": 0,
                    "teamScore": 0
                },
                "10": {
                    "participantId": 7,
                    "position": {
                        "x": 9430,
                        "y": 9220
                    },
                    "currentGold": 1015,
                    "totalGold": 9890,
                    "level": 14,
                    "xp": 12636,
                    "minionsKilled": 36,
                    "jungleMinionsKilled": 4,
                    "dominionScore": 0,
                    "teamScore": 0
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2041312,
                    "participantId": 8,
                    "itemId": 3026
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2041312,
                    "participantId": 8,
                    "itemId": 1038
                },
                {
                    "type": "ITEM_SOLD",
                    "timestamp": 2054029,
                    "participantId": 2,
                    "itemId": 2055
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2056804,
                    "participantId": 10,
                    "itemId": 2055
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2057068,
                    "participantId": 8,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2059250,
                    "participantId": 4,
                    "itemId": 3364
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2059250,
                    "participantId": 7,
                    "itemId": 3916
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2059250,
                    "participantId": 4,
                    "itemId": 3340
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2059250,
                    "participantId": 7,
                    "itemId": 1052
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2071969,
                    "participantId": 2,
                    "itemId": 1036
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 2079337,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 7
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2080427,
                    "participantId": 8,
                    "itemId": 2140
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2080427,
                    "participantId": 8,
                    "itemId": 2140
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 2088357,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 1
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2090669,
                    "participantId": 5,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 2093047,
                    "wardType": "BLUE_TRINKET",
                    "creatorId": 8
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2096259,
                    "participantId": 6,
                    "itemId": 3116
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2096259,
                    "participantId": 6,
                    "itemId": 1028
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 2099301,
                    "wardType": "BLUE_TRINKET",
                    "killerId": 4
                }
            ],
            "timestamp": 2100631
        },
        {
            "participantFrames": {
                "1": {
                    "participantId": 5,
                    "currentGold": -2,
                    "totalGold": 15098,
                    "level": 17,
                    "xp": 16863,
                    "minionsKilled": 158,
                    "jungleMinionsKilled": 32
                },
                "2": {
                    "participantId": 4,
                    "currentGold": 885,
                    "totalGold": 13335,
                    "level": 15,
                    "xp": 13614,
                    "minionsKilled": 21,
                    "jungleMinionsKilled": 116
                },
                "3": {
                    "participantId": 1,
                    "currentGold": 508,
                    "totalGold": 12858,
                    "level": 17,
                    "xp": 16673,
                    "minionsKilled": 186,
                    "jungleMinionsKilled": 12
                },
                "4": {
                    "participantId": 2,
                    "currentGold": 1031,
                    "totalGold": 12806,
                    "level": 15,
                    "xp": 13073,
                    "minionsKilled": 186,
                    "jungleMinionsKilled": 16
                },
                "5": {
                    "participantId": 3,
                    "currentGold": 2055,
                    "totalGold": 13430,
                    "level": 14,
                    "xp": 12531,
                    "minionsKilled": 54,
                    "jungleMinionsKilled": 4
                },
                "6": {
                    "participantId": 9,
                    "currentGold": 1181,
                    "totalGold": 12531,
                    "level": 16,
                    "xp": 15647,
                    "minionsKilled": 129,
                    "jungleMinionsKilled": 34
                },
                "7": {
                    "participantId": 10,
                    "currentGold": 711,
                    "totalGold": 9644,
                    "level": 14,
                    "xp": 12885,
                    "minionsKilled": 15,
                    "jungleMinionsKilled": 85
                },
                "8": {
                    "participantId": 6,
                    "currentGold": 322,
                    "totalGold": 13772,
                    "level": 18,
                    "xp": 18680,
                    "minionsKilled": 198,
                    "jungleMinionsKilled": 26
                },
                "9": {
                    "participantId": 8,
                    "currentGold": 757,
                    "totalGold": 18662,
                    "level": 17,
                    "xp": 17705,
                    "minionsKilled": 253,
                    "jungleMinionsKilled": 24
                },
                "10": {
                    "participantId": 7,
                    "currentGold": 1765,
                    "totalGold": 10640,
                    "level": 15,
                    "xp": 14062,
                    "minionsKilled": 38,
                    "jungleMinionsKilled": 4
                }
            },
            "events": [
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2100961,
                    "participantId": 6,
                    "itemId": 3363
                },
                {
                    "type": "ITEM_DESTROYED",
                    "timestamp": 2100961,
                    "participantId": 6,
                    "itemId": 3340
                },
                {
                    "type": "WARD_KILL",
                    "timestamp": 2108261,
                    "wardType": "CONTROL_WARD",
                    "killerId": 4
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 2110506,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 2111398,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "WARD_PLACED",
                    "timestamp": 2113876,
                    "wardType": "SIGHT_WARD",
                    "creatorId": 3
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2117213,
                    "participantId": 9,
                    "skillSlot": 4,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2124248,
                    "participantId": 1,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2130128,
                    "position": {
                        "x": 9920,
                        "y": 9446
                    },
                    "killerId": 10,
                    "victimId": 1,
                    "assistingParticipantIds": [
                        6,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2130953,
                    "position": {
                        "x": 10213,
                        "y": 9982
                    },
                    "killerId": 8,
                    "victimId": 5,
                    "assistingParticipantIds": [
                        9,
                        6,
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2131019,
                    "position": {
                        "x": 10113,
                        "y": 9802
                    },
                    "killerId": 3,
                    "victimId": 10,
                    "assistingParticipantIds": [
                        1,
                        2
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2133530,
                    "position": {
                        "x": 8963,
                        "y": 9562
                    },
                    "killerId": 9,
                    "victimId": 2,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2135425,
                    "position": {
                        "x": 11466,
                        "y": 10792
                    },
                    "killerId": 8,
                    "victimId": 4,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2136812,
                    "participantId": 6,
                    "skillSlot": 2,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 2138958,
                    "position": {
                        "x": 8791,
                        "y": 9993
                    },
                    "killerId": 9,
                    "victimId": 3,
                    "assistingParticipantIds": [
                        7
                    ]
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2140279,
                    "participantId": 2,
                    "skillSlot": 3,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "SKILL_LEVEL_UP",
                    "timestamp": 2146819,
                    "participantId": 7,
                    "skillSlot": 1,
                    "levelUpType": "NORMAL"
                },
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 2149000,
                    "participantId": 5,
                    "itemId": 2420
                }
            ],
            "timestamp": 2160631
        }
    ],
    "frameInterval": 60000
}

