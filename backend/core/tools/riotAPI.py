import requests
import asyncio
import os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.redis.Redis import RedisQueue
import time, datetime
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
    rq = {}
    rq["queueId"] = matchinfo["info"]["queueId"]
    rq["gameDuration"] = matchinfo["info"]["gameDuration"]
    rq["gameCreation"] = matchinfo["info"]["gameCreation"]
    rq["participants"] = {}
    for user in matchinfo["info"]["participants"]:
        
    
    return 1

async def api_match_matchid(session, rq, matchid):
    async with session.get(url_match_by_gameid.format(matchid), headers=headers) as resp:
        matchinfo = await resp.json()
        result = analyze_match(matchinfo)
        rq.setval(matchid, result)
        

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


{
    "queueId":,
    #"matchId":,
    "gameDuration":,
    "gameCreation":,
    "participants":{
        "1":{
            "summonerName":,
            "champion":,
            "level":,
            "cs":,
            "kills":,
            "deaths":,
            "assists":,
            "position":,
            "item0":,
            "item6":,
            "spell1":,
            "spell2":,
            "score":,
            "win":,
        },
        "2":,
        "3":,
    },

}


{
    "metadata": {
        "dataVersion": "2",
        "matchId": "KR_5164937811",
        "participants": [
            "22wylmILmNW8h-knHPZkqrNcG54SfgL1nhhym6kXP4sHafm9PlEHBx82_Ry_D9gcWe_xHFdeR8xWPw",
            "84mYlcb9rIpjeCEf54ezqtkKuysAtTOhhlkM1xvt-1yRUPVQjmhX_IzAPocfc7QBbfXYBv9vzRgB-w",
            "j7tkab6wdBGvTJQToEzjkjS8x-KvlOTL-Zpq4tzB_EZv8Ftrko71ndA1edMc6ueSQLNy5bRgsGxSPg",
            "UgxZESsWLRBt23ZANkbKwoFKNPNWzJ-YYgpzdqASwmBCceNgTvx39kWQp5Bp4LJ-fe1reKkEtyjBUQ",
            "mKpkNsAINt4OYnqAt0ILfqt_jgdeHEV663GHZ9ieNs4taXyaDrFBGo0iIACAHjrLIHRe_Fk5eWcJUQ",
            "KETkNdY0hySnibldRs51ylw8lUIuttV67Jg09SVzmT4hwyQvpUmAnWrMGoO29yfOBfMAPLeLLyBY8g",
            "M6ptB20pcLB9UEspTONDuch2jwB4HCR8tReWWMciY9CNHOi-bNFY3k6nYcXQwR4TYdz7eP5od_UuAw",
            "JVBIi7XAWmNvrMelYNn00_8d5btC2lpwqnG-eWhq8YVqezhPstpXCdSunS_6f-P2dh7ZuEQT_x59_A",
            "N96U05GeK8PSV_vmN9cYptK1Cq7QZY_UNlB0mm1IlmuAI4T0HnYqt03xW21_fCu38jB0OOtJ-pf92Q",
            "4YdTygmcwrYwMz2ZXYEEVCWTC8KtnZvvltorfhMbnMwZD2q7K3pmlghl-5mVJ_Xwp9UbGKCSYpLnag"
        ]
    },
    "info": {
        "gameCreation": 1619849422000,
        "gameDuration": 986133,
        "gameId": 5164937811,
        "gameMode": "CLASSIC",
        "gameName": "teambuilder-match-5164937811",
        "gameStartTimestamp": 1619849529551,
        "gameType": "MATCHED_GAME",
        "gameVersion": "11.9.372.2066",
        "mapId": 11,
        "participants": [
            {
                "assists": 2,
                "baronKills": 0,
                "bountyLevel": 2,
                "champExperience": 8249,
                "champLevel": 11,
                "championId": 39,
                "championName": "Irelia",
                "championTransform": 0,
                "consumablesPurchased": 1,
                "damageDealtToBuildings": 5653,
                "damageDealtToObjectives": 6241,
                "damageDealtToTurrets": 5653,
                "damageSelfMitigated": 3482,
                "deaths": 2,
                "detectorWardsPlaced": 0,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 7276,
                "goldSpent": 6050,
                "individualPosition": "TOP",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 1055,
                "item1": 2031,
                "item2": 3153,
                "item3": 3057,
                "item4": 3047,
                "item5": 1028,
                "item6": 3340,
                "itemsPurchased": 12,
                "killingSprees": 1,
                "kills": 2,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 2,
                "largestMultiKill": 1,
                "longestTimeSpentLiving": 205,
                "magicDamageDealt": 7397,
                "magicDamageDealtToChampions": 1574,
                "magicDamageTaken": 161,
                "neutralMinionsKilled": 2,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 1,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5005
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8010,
                                    "var1": 187,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8009,
                                    "var1": 486,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 9103,
                                    "var1": 0,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8299,
                                    "var1": 175,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8143,
                                    "var1": 143,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8135,
                                    "var1": 0,
                                    "var2": 2,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        }
                    ]
                },
                "physicalDamageDealt": 56183,
                "physicalDamageDealtToChampions": 2706,
                "physicalDamageTaken": 5006,
                "profileIcon": 20,
                "puuid": "22wylmILmNW8h-knHPZkqrNcG54SfgL1nhhym6kXP4sHafm9PlEHBx82_Ry_D9gcWe_xHFdeR8xWPw",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 124,
                "spell2Casts": 9,
                "spell3Casts": 19,
                "spell4Casts": 2,
                "summoner1Casts": 1,
                "summoner1Id": 4,
                "summoner2Casts": 2,
                "summoner2Id": 14,
                "summonerId": "o-4kSktku4PZR8M0PdMeaOcThjZSHqQMOEdUztJl3sMwkuY",
                "summonerLevel": 220,
                "summonerName": "원스타교장샘",
                "teamEarlySurrendered": false,
                "teamId": 100,
                "teamPosition": "TOP",
                "timeCCingOthers": 5,
                "timePlayed": 986,
                "totalDamageDealt": 63791,
                "totalDamageDealtToChampions": 4490,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 5781,
                "totalHeal": 950,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 120,
                "totalTimeCCDealt": 21,
                "totalTimeSpentDead": 22,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 210,
                "trueDamageDealtToChampions": 210,
                "trueDamageTaken": 613,
                "turretKills": 1,
                "turretsLost": 0,
                "unrealKills": 0,
                "visionScore": 0,
                "visionWardsBoughtInGame": 0,
                "wardsKilled": 0,
                "wardsPlaced": 0,
                "win": true
            },
            {
                "assists": 5,
                "baronKills": 0,
                "bountyLevel": 3,
                "champExperience": 6085,
                "champLevel": 9,
                "championId": 64,
                "championName": "LeeSin",
                "championTransform": 0,
                "consumablesPurchased": 5,
                "damageDealtToBuildings": 371,
                "damageDealtToObjectives": 14559,
                "damageDealtToTurrets": 371,
                "damageSelfMitigated": 8983,
                "deaths": 1,
                "detectorWardsPlaced": 4,
                "doubleKills": 1,
                "dragonKills": 1,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 7340,
                "goldSpent": 6875,
                "individualPosition": "JUNGLE",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 6692,
                "item1": 3158,
                "item2": 2055,
                "item3": 3134,
                "item4": 1028,
                "item5": 1036,
                "item6": 3340,
                "itemsPurchased": 16,
                "killingSprees": 2,
                "kills": 7,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 4,
                "largestMultiKill": 2,
                "longestTimeSpentLiving": 684,
                "magicDamageDealt": 11019,
                "magicDamageDealtToChampions": 1372,
                "magicDamageTaken": 1674,
                "neutralMinionsKilled": 69,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 2,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5005
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8010,
                                    "var1": 131,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 9111,
                                    "var1": 399,
                                    "var2": 240,
                                    "var3": 0
                                },
                                {
                                    "perk": 9105,
                                    "var1": 8,
                                    "var2": 40,
                                    "var3": 0
                                },
                                {
                                    "perk": 8014,
                                    "var1": 244,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8143,
                                    "var1": 214,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8135,
                                    "var1": 0,
                                    "var2": 5,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        }
                    ]
                },
                "physicalDamageDealt": 38621,
                "physicalDamageDealtToChampions": 6829,
                "physicalDamageTaken": 8980,
                "profileIcon": 4923,
                "puuid": "84mYlcb9rIpjeCEf54ezqtkKuysAtTOhhlkM1xvt-1yRUPVQjmhX_IzAPocfc7QBbfXYBv9vzRgB-w",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 98,
                "spell2Casts": 107,
                "spell3Casts": 70,
                "spell4Casts": 3,
                "summoner1Casts": 10,
                "summoner1Id": 11,
                "summoner2Casts": 1,
                "summoner2Id": 4,
                "summonerId": "moD0yZQY5s_khKHuVORkYpg8Q-14pj8qk3gZPtIlBWcDfhU",
                "summonerLevel": 111,
                "summonerName": "방호학과 김닥터",
                "teamEarlySurrendered": false,
                "teamId": 100,
                "teamPosition": "JUNGLE",
                "timeCCingOthers": 8,
                "timePlayed": 986,
                "totalDamageDealt": 59101,
                "totalDamageDealtToChampions": 8680,
                "totalDamageShieldedOnTeammates": 263,
                "totalDamageTaken": 11205,
                "totalHeal": 3413,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 10,
                "totalTimeCCDealt": 277,
                "totalTimeSpentDead": 21,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 9460,
                "trueDamageDealtToChampions": 478,
                "trueDamageTaken": 550,
                "turretKills": 0,
                "turretsLost": 0,
                "unrealKills": 0,
                "visionScore": 23,
                "visionWardsBoughtInGame": 5,
                "wardsKilled": 1,
                "wardsPlaced": 9,
                "win": true
            },
            {
                "assists": 4,
                "baronKills": 0,
                "bountyLevel": 2,
                "champExperience": 6948,
                "champLevel": 10,
                "championId": 245,
                "championName": "Ekko",
                "championTransform": 0,
                "consumablesPurchased": 2,
                "damageDealtToBuildings": 1963,
                "damageDealtToObjectives": 5517,
                "damageDealtToTurrets": 1963,
                "damageSelfMitigated": 3215,
                "deaths": 2,
                "detectorWardsPlaced": 0,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 6300,
                "goldSpent": 5175,
                "individualPosition": "MIDDLE",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 2033,
                "item1": 2055,
                "item2": 3020,
                "item3": 4636,
                "item4": 1029,
                "item5": 0,
                "item6": 3340,
                "itemsPurchased": 8,
                "killingSprees": 1,
                "kills": 2,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 2,
                "largestMultiKill": 1,
                "longestTimeSpentLiving": 129,
                "magicDamageDealt": 35785,
                "magicDamageDealtToChampions": 4599,
                "magicDamageTaken": 381,
                "neutralMinionsKilled": 4,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 3,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5003,
                        "flex": 5008,
                        "offense": 5008
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8112,
                                    "var1": 335,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8139,
                                    "var1": 404,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8120,
                                    "var1": 0,
                                    "var2": 6,
                                    "var3": 3
                                },
                                {
                                    "perk": 8135,
                                    "var1": 0,
                                    "var2": 3,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8210,
                                    "var1": 0,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8236,
                                    "var1": 8,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8200
                        }
                    ]
                },
                "physicalDamageDealt": 8056,
                "physicalDamageDealtToChampions": 1131,
                "physicalDamageTaken": 5950,
                "profileIcon": 4423,
                "puuid": "j7tkab6wdBGvTJQToEzjkjS8x-KvlOTL-Zpq4tzB_EZv8Ftrko71ndA1edMc6ueSQLNy5bRgsGxSPg",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 54,
                "spell2Casts": 6,
                "spell3Casts": 31,
                "spell4Casts": 0,
                "summoner1Casts": 2,
                "summoner1Id": 12,
                "summoner2Casts": 2,
                "summoner2Id": 4,
                "summonerId": "oN1t1jCg2U00m_eg1c1UYJSAK5w_TUllDCyiqPXkYa3a2L0",
                "summonerLevel": 375,
                "summonerName": "juicy world",
                "teamEarlySurrendered": false,
                "teamId": 100,
                "teamPosition": "MIDDLE",
                "timeCCingOthers": 7,
                "timePlayed": 986,
                "totalDamageDealt": 47745,
                "totalDamageDealtToChampions": 5796,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 7043,
                "totalHeal": 495,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 96,
                "totalTimeCCDealt": 153,
                "totalTimeSpentDead": 14,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 3903,
                "trueDamageDealtToChampions": 66,
                "trueDamageTaken": 712,
                "turretKills": 1,
                "turretsLost": 0,
                "unrealKills": 0,
                "visionScore": 10,
                "visionWardsBoughtInGame": 2,
                "wardsKilled": 1,
                "wardsPlaced": 5,
                "win": true
            },
            {
                "assists": 6,
                "baronKills": 0,
                "bountyLevel": 5,
                "champExperience": 6581,
                "champLevel": 10,
                "championId": 101,
                "championName": "Xerath",
                "championTransform": 0,
                "consumablesPurchased": 1,
                "damageDealtToBuildings": 1526,
                "damageDealtToObjectives": 5336,
                "damageDealtToTurrets": 1526,
                "damageSelfMitigated": 1767,
                "deaths": 1,
                "detectorWardsPlaced": 1,
                "doubleKills": 3,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 8520,
                "goldSpent": 7195,
                "individualPosition": "BOTTOM",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 6653,
                "item1": 1052,
                "item2": 1052,
                "item3": 0,
                "item4": 3041,
                "item5": 3020,
                "item6": 3363,
                "itemsPurchased": 16,
                "killingSprees": 2,
                "kills": 10,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 5,
                "largestMultiKill": 2,
                "longestTimeSpentLiving": 653,
                "magicDamageDealt": 41916,
                "magicDamageDealtToChampions": 9117,
                "magicDamageTaken": 620,
                "neutralMinionsKilled": 0,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 4,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5008
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8128,
                                    "var1": 947,
                                    "var2": 15,
                                    "var3": 0
                                },
                                {
                                    "perk": 8126,
                                    "var1": 190,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8138,
                                    "var1": 30,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8106,
                                    "var1": 5,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8009,
                                    "var1": 2042,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8014,
                                    "var1": 369,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        }
                    ]
                },
                "physicalDamageDealt": 6771,
                "physicalDamageDealtToChampions": 784,
                "physicalDamageTaken": 3731,
                "profileIcon": 4661,
                "puuid": "UgxZESsWLRBt23ZANkbKwoFKNPNWzJ-YYgpzdqASwmBCceNgTvx39kWQp5Bp4LJ-fe1reKkEtyjBUQ",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 54,
                "spell2Casts": 29,
                "spell3Casts": 17,
                "spell4Casts": 16,
                "summoner1Casts": 2,
                "summoner1Id": 4,
                "summoner2Casts": 3,
                "summoner2Id": 3,
                "summonerId": "W5qKSXlmwqxF5z6Gnj3B6UNP5rJGFHKs_FVsLkSkhic46iw",
                "summonerLevel": 437,
                "summonerName": "일단샤코픽한다",
                "teamEarlySurrendered": false,
                "teamId": 100,
                "teamPosition": "BOTTOM",
                "timeCCingOthers": 13,
                "timePlayed": 986,
                "totalDamageDealt": 48879,
                "totalDamageDealtToChampions": 10093,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 4351,
                "totalHeal": 270,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 94,
                "totalTimeCCDealt": 68,
                "totalTimeSpentDead": 21,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 190,
                "trueDamageDealtToChampions": 190,
                "trueDamageTaken": 0,
                "turretKills": 0,
                "turretsLost": 0,
                "unrealKills": 0,
                "visionScore": 11,
                "visionWardsBoughtInGame": 1,
                "wardsKilled": 1,
                "wardsPlaced": 6,
                "win": true
            },
            {
                "assists": 12,
                "baronKills": 0,
                "bountyLevel": 0,
                "champExperience": 5634,
                "champLevel": 9,
                "championId": 80,
                "championName": "Pantheon",
                "championTransform": 0,
                "consumablesPurchased": 3,
                "damageDealtToBuildings": 1075,
                "damageDealtToObjectives": 2468,
                "damageDealtToTurrets": 1075,
                "damageSelfMitigated": 4647,
                "deaths": 3,
                "detectorWardsPlaced": 1,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 6577,
                "goldSpent": 6375,
                "individualPosition": "UTILITY",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 3047,
                "item1": 3855,
                "item2": 6692,
                "item3": 3133,
                "item4": 1028,
                "item5": 0,
                "item6": 3364,
                "itemsPurchased": 19,
                "killingSprees": 1,
                "kills": 4,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 3,
                "largestMultiKill": 1,
                "longestTimeSpentLiving": 440,
                "magicDamageDealt": 0,
                "magicDamageDealtToChampions": 0,
                "magicDamageTaken": 1578,
                "neutralMinionsKilled": 0,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 5,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5008
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8005,
                                    "var1": 1270,
                                    "var2": 700,
                                    "var3": 569
                                },
                                {
                                    "perk": 9111,
                                    "var1": 452,
                                    "var2": 320,
                                    "var3": 0
                                },
                                {
                                    "perk": 9105,
                                    "var1": 11,
                                    "var2": 30,
                                    "var3": 0
                                },
                                {
                                    "perk": 8014,
                                    "var1": 121,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8126,
                                    "var1": 304,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8105,
                                    "var1": 13,
                                    "var2": 5,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        }
                    ]
                },
                "physicalDamageDealt": 20308,
                "physicalDamageDealtToChampions": 9771,
                "physicalDamageTaken": 5621,
                "profileIcon": 4794,
                "puuid": "mKpkNsAINt4OYnqAt0ILfqt_jgdeHEV663GHZ9ieNs4taXyaDrFBGo0iIACAHjrLIHRe_Fk5eWcJUQ",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 28,
                "spell2Casts": 18,
                "spell3Casts": 10,
                "spell4Casts": 0,
                "summoner1Casts": 3,
                "summoner1Id": 14,
                "summoner2Casts": 3,
                "summoner2Id": 4,
                "summonerId": "EMFf6_au0cUX8NPIsIVwIjJlVveKKN-1lGWIehscV3lgajM",
                "summonerLevel": 246,
                "summonerName": "Depraved God",
                "teamEarlySurrendered": false,
                "teamId": 100,
                "teamPosition": "UTILITY",
                "timeCCingOthers": 14,
                "timePlayed": 986,
                "totalDamageDealt": 24491,
                "totalDamageDealtToChampions": 10235,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 8453,
                "totalHeal": 922,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 22,
                "totalTimeCCDealt": 16,
                "totalTimeSpentDead": 69,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 4183,
                "trueDamageDealtToChampions": 464,
                "trueDamageTaken": 1254,
                "turretKills": 1,
                "turretsLost": 0,
                "unrealKills": 0,
                "visionScore": 22,
                "visionWardsBoughtInGame": 1,
                "wardsKilled": 2,
                "wardsPlaced": 7,
                "win": true
            },
            {
                "assists": 0,
                "baronKills": 0,
                "bountyLevel": 0,
                "champExperience": 5707,
                "champLevel": 9,
                "championId": 875,
                "championName": "Sett",
                "championTransform": 0,
                "consumablesPurchased": 1,
                "damageDealtToBuildings": 955,
                "damageDealtToObjectives": 955,
                "damageDealtToTurrets": 955,
                "damageSelfMitigated": 7023,
                "deaths": 5,
                "detectorWardsPlaced": 0,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 5169,
                "goldSpent": 4600,
                "individualPosition": "TOP",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 6631,
                "item1": 2031,
                "item2": 1036,
                "item3": 1054,
                "item4": 1042,
                "item5": 0,
                "item6": 3340,
                "itemsPurchased": 10,
                "killingSprees": 1,
                "kills": 3,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 2,
                "largestMultiKill": 1,
                "longestTimeSpentLiving": 298,
                "magicDamageDealt": 0,
                "magicDamageDealtToChampions": 0,
                "magicDamageTaken": 4009,
                "neutralMinionsKilled": 0,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 6,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5005
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8010,
                                    "var1": 248,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 9111,
                                    "var1": 191,
                                    "var2": 60,
                                    "var3": 0
                                },
                                {
                                    "perk": 9104,
                                    "var1": 0,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8299,
                                    "var1": 311,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8444,
                                    "var1": 317,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8451,
                                    "var1": 102,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8400
                        }
                    ]
                },
                "physicalDamageDealt": 33520,
                "physicalDamageDealtToChampions": 7258,
                "physicalDamageTaken": 6208,
                "profileIcon": 4491,
                "puuid": "KETkNdY0hySnibldRs51ylw8lUIuttV67Jg09SVzmT4hwyQvpUmAnWrMGoO29yfOBfMAPLeLLyBY8g",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 23,
                "spell2Casts": 10,
                "spell3Casts": 18,
                "spell4Casts": 3,
                "summoner1Casts": 2,
                "summoner1Id": 12,
                "summoner2Casts": 2,
                "summoner2Id": 4,
                "summonerId": "kA6mQxR6ISkbVVvxPufe7GL6i_j4WNg5Rfc6fuTiqHdwJkw",
                "summonerLevel": 278,
                "summonerName": "다리우스바샛끼",
                "teamEarlySurrendered": false,
                "teamId": 200,
                "teamPosition": "TOP",
                "timeCCingOthers": 15,
                "timePlayed": 986,
                "totalDamageDealt": 36834,
                "totalDamageDealtToChampions": 9451,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 10691,
                "totalHeal": 422,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 76,
                "totalTimeCCDealt": 96,
                "totalTimeSpentDead": 91,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 3313,
                "trueDamageDealtToChampions": 2192,
                "trueDamageTaken": 474,
                "turretKills": 0,
                "turretsLost": 4,
                "unrealKills": 0,
                "visionScore": 7,
                "visionWardsBoughtInGame": 0,
                "wardsKilled": 0,
                "wardsPlaced": 5,
                "win": false
            },
            {
                "assists": 4,
                "baronKills": 0,
                "bountyLevel": 0,
                "champExperience": 6355,
                "champLevel": 10,
                "championId": 36,
                "championName": "DrMundo",
                "championTransform": 0,
                "consumablesPurchased": 1,
                "damageDealtToBuildings": 0,
                "damageDealtToObjectives": 2652,
                "damageDealtToTurrets": 0,
                "damageSelfMitigated": 9020,
                "deaths": 5,
                "detectorWardsPlaced": 1,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 5219,
                "goldSpent": 4075,
                "individualPosition": "JUNGLE",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 2422,
                "item1": 2031,
                "item2": 3068,
                "item3": 1029,
                "item4": 0,
                "item5": 0,
                "item6": 3340,
                "itemsPurchased": 13,
                "killingSprees": 0,
                "kills": 0,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 0,
                "largestMultiKill": 0,
                "longestTimeSpentLiving": 267,
                "magicDamageDealt": 47077,
                "magicDamageDealtToChampions": 1869,
                "magicDamageTaken": 4752,
                "neutralMinionsKilled": 92,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 7,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5005
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8021,
                                    "var1": 859,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 9111,
                                    "var1": 249,
                                    "var2": 80,
                                    "var3": 0
                                },
                                {
                                    "perk": 9105,
                                    "var1": 13,
                                    "var2": 40,
                                    "var3": 0
                                },
                                {
                                    "perk": 8299,
                                    "var1": 166,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8304,
                                    "var1": 10,
                                    "var2": 3,
                                    "var3": 0
                                },
                                {
                                    "perk": 8410,
                                    "var1": 21,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8300
                        }
                    ]
                },
                "physicalDamageDealt": 20725,
                "physicalDamageDealtToChampions": 1256,
                "physicalDamageTaken": 10775,
                "profileIcon": 4923,
                "puuid": "M6ptB20pcLB9UEspTONDuch2jwB4HCR8tReWWMciY9CNHOi-bNFY3k6nYcXQwR4TYdz7eP5od_UuAw",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 87,
                "spell2Casts": 63,
                "spell3Casts": 50,
                "spell4Casts": 3,
                "summoner1Casts": 8,
                "summoner1Id": 11,
                "summoner2Casts": 2,
                "summoner2Id": 4,
                "summonerId": "dQcARkFXZ7O60lYOZFU1PA_czNLu00V9ghGVZHC5LmM_tA8",
                "summonerLevel": 245,
                "summonerName": "착한댕댕이 워윅",
                "teamEarlySurrendered": false,
                "teamId": 200,
                "teamPosition": "JUNGLE",
                "timeCCingOthers": 4,
                "timePlayed": 986,
                "totalDamageDealt": 73384,
                "totalDamageDealtToChampions": 3424,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 15774,
                "totalHeal": 10171,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 25,
                "totalTimeCCDealt": 214,
                "totalTimeSpentDead": 91,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 5582,
                "trueDamageDealtToChampions": 298,
                "trueDamageTaken": 247,
                "turretKills": 0,
                "turretsLost": 4,
                "unrealKills": 0,
                "visionScore": 9,
                "visionWardsBoughtInGame": 1,
                "wardsKilled": 1,
                "wardsPlaced": 4,
                "win": false
            },
            {
                "assists": 0,
                "baronKills": 0,
                "bountyLevel": 0,
                "champExperience": 5981,
                "champLevel": 9,
                "championId": 238,
                "championName": "Zed",
                "championTransform": 0,
                "consumablesPurchased": 5,
                "damageDealtToBuildings": 0,
                "damageDealtToObjectives": 142,
                "damageDealtToTurrets": 0,
                "damageSelfMitigated": 4178,
                "deaths": 3,
                "detectorWardsPlaced": 0,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": true,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 5338,
                "goldSpent": 5275,
                "individualPosition": "MIDDLE",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 2031,
                "item1": 6630,
                "item2": 1055,
                "item3": 3111,
                "item4": 0,
                "item5": 0,
                "item6": 3340,
                "itemsPurchased": 14,
                "killingSprees": 1,
                "kills": 4,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 3,
                "largestMultiKill": 1,
                "longestTimeSpentLiving": 696,
                "magicDamageDealt": 2066,
                "magicDamageDealtToChampions": 96,
                "magicDamageTaken": 3918,
                "neutralMinionsKilled": 0,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 8,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5007
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8010,
                                    "var1": 65,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8009,
                                    "var1": 309,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 9103,
                                    "var1": 0,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8014,
                                    "var1": 115,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8106,
                                    "var1": 3,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8139,
                                    "var1": 431,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        }
                    ]
                },
                "physicalDamageDealt": 25404,
                "physicalDamageDealtToChampions": 5505,
                "physicalDamageTaken": 5456,
                "profileIcon": 1670,
                "puuid": "JVBIi7XAWmNvrMelYNn00_8d5btC2lpwqnG-eWhq8YVqezhPstpXCdSunS_6f-P2dh7ZuEQT_x59_A",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 46,
                "spell2Casts": 40,
                "spell3Casts": 25,
                "spell4Casts": 6,
                "summoner1Casts": 3,
                "summoner1Id": 14,
                "summoner2Casts": 3,
                "summoner2Id": 4,
                "summonerId": "w3DLzbivLpkJdTLtQPwbkjduoBd6C_zcf6T6OhKOBEWmfRU",
                "summonerLevel": 105,
                "summonerName": "qqweerw",
                "teamEarlySurrendered": false,
                "teamId": 200,
                "teamPosition": "MIDDLE",
                "timeCCingOthers": 1,
                "timePlayed": 986,
                "totalDamageDealt": 27861,
                "totalDamageDealtToChampions": 5991,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 9669,
                "totalHeal": 481,
                "totalHealsOnTeammates": 0,
                "totalMinionsKilled": 82,
                "totalTimeCCDealt": 20,
                "totalTimeSpentDead": 55,
                "totalUnitsHealed": 1,
                "tripleKills": 0,
                "trueDamageDealt": 390,
                "trueDamageDealtToChampions": 390,
                "trueDamageTaken": 295,
                "turretKills": 0,
                "turretsLost": 4,
                "unrealKills": 0,
                "visionScore": 8,
                "visionWardsBoughtInGame": 1,
                "wardsKilled": 1,
                "wardsPlaced": 5,
                "win": false
            },
            {
                "assists": 1,
                "baronKills": 0,
                "bountyLevel": 0,
                "champExperience": 4782,
                "champLevel": 8,
                "championId": 18,
                "championName": "Tristana",
                "championTransform": 0,
                "consumablesPurchased": 2,
                "damageDealtToBuildings": 0,
                "damageDealtToObjectives": 2190,
                "damageDealtToTurrets": 0,
                "damageSelfMitigated": 2599,
                "deaths": 7,
                "detectorWardsPlaced": 0,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 5397,
                "goldSpent": 4425,
                "individualPosition": "BOTTOM",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 1055,
                "item1": 1018,
                "item2": 6670,
                "item3": 3006,
                "item4": 1037,
                "item5": 0,
                "item6": 3340,
                "itemsPurchased": 11,
                "killingSprees": 0,
                "kills": 2,
                "lane": "NONE",
                "largestCriticalStrike": 1907,
                "largestKillingSpree": 0,
                "largestMultiKill": 1,
                "longestTimeSpentLiving": 196,
                "magicDamageDealt": 7475,
                "magicDamageDealtToChampions": 455,
                "magicDamageTaken": 2855,
                "neutralMinionsKilled": 0,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 9,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5002,
                        "flex": 5008,
                        "offense": 5005
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 9923,
                                    "var1": 22,
                                    "var2": 91,
                                    "var3": 0
                                },
                                {
                                    "perk": 8139,
                                    "var1": 207,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8138,
                                    "var1": 3,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8135,
                                    "var1": 0,
                                    "var2": 3,
                                    "var3": 0
                                }
                            ],
                            "style": 8100
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8009,
                                    "var1": 223,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8014,
                                    "var1": 59,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8000
                        }
                    ]
                },
                "physicalDamageDealt": 23756,
                "physicalDamageDealtToChampions": 3449,
                "physicalDamageTaken": 5757,
                "profileIcon": 4655,
                "puuid": "N96U05GeK8PSV_vmN9cYptK1Cq7QZY_UNlB0mm1IlmuAI4T0HnYqt03xW21_fCu38jB0OOtJ-pf92Q",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 9,
                "spell2Casts": 13,
                "spell3Casts": 11,
                "spell4Casts": 1,
                "summoner1Casts": 2,
                "summoner1Id": 7,
                "summoner2Casts": 2,
                "summoner2Id": 4,
                "summonerId": "fgrPXI9DE5VgnoVIClCvJjk7ofavx6SjalcRRB3UX0jJIw0",
                "summonerLevel": 121,
                "summonerName": "으나 누나",
                "teamEarlySurrendered": false,
                "teamId": 200,
                "teamPosition": "BOTTOM",
                "timeCCingOthers": 1,
                "timePlayed": 986,
                "totalDamageDealt": 33139,
                "totalDamageDealtToChampions": 3904,
                "totalDamageShieldedOnTeammates": 0,
                "totalDamageTaken": 8917,
                "totalHeal": 578,
                "totalHealsOnTeammates": 270,
                "totalMinionsKilled": 83,
                "totalTimeCCDealt": 7,
                "totalTimeSpentDead": 114,
                "totalUnitsHealed": 3,
                "tripleKills": 0,
                "trueDamageDealt": 1907,
                "trueDamageDealtToChampions": 0,
                "trueDamageTaken": 304,
                "turretKills": 0,
                "turretsLost": 4,
                "unrealKills": 0,
                "visionScore": 7,
                "visionWardsBoughtInGame": 0,
                "wardsKilled": 0,
                "wardsPlaced": 5,
                "win": false
            },
            {
                "assists": 2,
                "baronKills": 0,
                "bountyLevel": 0,
                "champExperience": 3241,
                "champLevel": 7,
                "championId": 412,
                "championName": "Thresh",
                "championTransform": 0,
                "consumablesPurchased": 4,
                "damageDealtToBuildings": 0,
                "damageDealtToObjectives": 0,
                "damageDealtToTurrets": 0,
                "damageSelfMitigated": 3433,
                "deaths": 5,
                "detectorWardsPlaced": 1,
                "doubleKills": 0,
                "dragonKills": 0,
                "firstBloodAssist": false,
                "firstBloodKill": false,
                "firstTowerAssist": false,
                "firstTowerKill": false,
                "gameEndedInEarlySurrender": false,
                "gameEndedInSurrender": true,
                "goldEarned": 3297,
                "goldSpent": 2400,
                "individualPosition": "UTILITY",
                "inhibitorKills": 0,
                "inhibitorsLost": 0,
                "item0": 1033,
                "item1": 3855,
                "item2": 2055,
                "item3": 3117,
                "item4": 1029,
                "item5": 0,
                "item6": 3364,
                "itemsPurchased": 11,
                "killingSprees": 0,
                "kills": 0,
                "lane": "NONE",
                "largestCriticalStrike": 0,
                "largestKillingSpree": 0,
                "largestMultiKill": 0,
                "longestTimeSpentLiving": 219,
                "magicDamageDealt": 3689,
                "magicDamageDealtToChampions": 1334,
                "magicDamageTaken": 3205,
                "neutralMinionsKilled": 0,
                "nexusKills": 0,
                "nexusLost": 0,
                "objectivesStolen": 0,
                "objectivesStolenAssists": 0,
                "participantId": 10,
                "pentaKills": 0,
                "perks": {
                    "statPerks": {
                        "defense": 5001,
                        "flex": 5002,
                        "offense": 5007
                    },
                    "styles": [
                        {
                            "description": "primaryStyle",
                            "selections": [
                                {
                                    "perk": 8439,
                                    "var1": 163,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8463,
                                    "var1": 204,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8473,
                                    "var1": 228,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8451,
                                    "var1": 39,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8400
                        },
                        {
                            "description": "subStyle",
                            "selections": [
                                {
                                    "perk": 8345,
                                    "var1": 3,
                                    "var2": 0,
                                    "var3": 0
                                },
                                {
                                    "perk": 8347,
                                    "var1": 0,
                                    "var2": 0,
                                    "var3": 0
                                }
                            ],
                            "style": 8300
                        }
                    ]
                },
                "physicalDamageDealt": 3183,
                "physicalDamageDealtToChampions": 399,
                "physicalDamageTaken": 2767,
                "profileIcon": 4490,
                "puuid": "4YdTygmcwrYwMz2ZXYEEVCWTC8KtnZvvltorfhMbnMwZD2q7K3pmlghl-5mVJ_Xwp9UbGKCSYpLnag",
                "quadraKills": 0,
                "riotIdName": "",
                "riotIdTagline": "",
                "role": "SUPPORT",
                "sightWardsBoughtInGame": 0,
                "spell1Casts": 10,
                "spell2Casts": 8,
                "spell3Casts": 11,
                "spell4Casts": 1,
                "summoner1Casts": 2,
                "summoner1Id": 14,
                "summoner2Casts": 2,
                "summoner2Id": 4,
                "summonerId": "c9gTJf7lKPUebFMlzE4ef4C4yO9tcTeUoGKdxeqByXneuA",
                "summonerLevel": 147,
                "summonerName": "말걸면던지는계정",
                "teamEarlySurrendered": false,
                "teamId": 200,
                "teamPosition": "UTILITY",
                "timeCCingOthers": 11,
                "timePlayed": 986,
                "totalDamageDealt": 8766,
                "totalDamageDealtToChampions": 1983,
                "totalDamageShieldedOnTeammates": 98,
                "totalDamageTaken": 6059,
                "totalHeal": 146,
                "totalHealsOnTeammates": 159,
                "totalMinionsKilled": 24,
                "totalTimeCCDealt": 37,
                "totalTimeSpentDead": 66,
                "totalUnitsHealed": 2,
                "tripleKills": 0,
                "trueDamageDealt": 1893,
                "trueDamageDealtToChampions": 250,
                "trueDamageTaken": 87,
                "turretKills": 0,
                "turretsLost": 4,
                "unrealKills": 0,
                "visionScore": 6,
                "visionWardsBoughtInGame": 2,
                "wardsKilled": 1,
                "wardsPlaced": 3,
                "win": false
            }
        ],
        "platformId": "KR",
        "queueId": 420,
        "teams": [
            {
                "bans": [
                    {
                        "championId": 35,
                        "pickTurn": 1
                    },
                    {
                        "championId": 25,
                        "pickTurn": 2
                    },
                    {
                        "championId": 53,
                        "pickTurn": 3
                    },
                    {
                        "championId": -1,
                        "pickTurn": 4
                    },
                    {
                        "championId": 90,
                        "pickTurn": 5
                    }
                ],
                "objectives": {
                    "baron": {
                        "first": false,
                        "kills": 0
                    },
                    "champion": {
                        "first": false,
                        "kills": 25
                    },
                    "dragon": {
                        "first": true,
                        "kills": 1
                    },
                    "inhibitor": {
                        "first": false,
                        "kills": 0
                    },
                    "riftHerald": {
                        "first": true,
                        "kills": 2
                    },
                    "tower": {
                        "first": true,
                        "kills": 4
                    }
                },
                "teamId": 100,
                "win": true
            },
            {
                "bans": [
                    {
                        "championId": 360,
                        "pickTurn": 6
                    },
                    {
                        "championId": 35,
                        "pickTurn": 7
                    },
                    {
                        "championId": -1,
                        "pickTurn": 8
                    },
                    {
                        "championId": 7,
                        "pickTurn": 9
                    },
                    {
                        "championId": 17,
                        "pickTurn": 10
                    }
                ],
                "objectives": {
                    "baron": {
                        "first": false,
                        "kills": 0
                    },
                    "champion": {
                        "first": true,
                        "kills": 9
                    },
                    "dragon": {
                        "first": false,
                        "kills": 0
                    },
                    "inhibitor": {
                        "first": false,
                        "kills": 0
                    },
                    "riftHerald": {
                        "first": false,
                        "kills": 0
                    },
                    "tower": {
                        "first": false,
                        "kills": 0
                    }
                },
                "teamId": 200,
                "win": false
            }
        ]
    }
}