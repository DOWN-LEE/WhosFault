API_KEY='RGAPI-d6011f1c-08a3-4898-97b2-5f6d0b13e393'
headers = {'X-Riot-Token':API_KEY}


url_by_name = 'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/'
url_rank_by_summonerid = 'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/'
url_matchlist_by_accontid = 'https://kr.api.riotgames.com/lol/match/v4/matchlists/by-account/'
url_match_by_gameid = 'https://kr.api.riotgames.com/lol/match/v4/matches/'
url_timeline_by_gameid = 'https://kr.api.riotgames.com/lol/match/v4/timelines/by-match/'


def rankToNum(tier, rank):
    '''
    rank 정보를 숫자로 변환
    '''
    result = ''
    num=''

    if rank == 'IV':
        num = '4'
    else:
        num = str(len(rank))
    

    if tier == 'IRON':
        result = num
    elif tier == 'BRONZE':
        result = '1' + num
    elif tier == 'SILVER':
        result = '2' + num
    elif tier == 'GOLD':
        result = '3' + num
    elif tier == 'PLATINUM':
        result = '4' + num
    elif tier == 'DIAMOND':
        result = '5' + num
    elif tier == 'MASTER':
        result = '6' + num
    elif tier == 'GRANDMASTER':
        result = '7' + num
    elif tier == 'CHALLENGER':
        result = '8' + num
    
    return int(result)
    



def calScore(matchinfo, matchtimeline, lane):
    
    lineMatch = {}
    if len(matchtimeline) <= 13:
        lineMatch = matchtimeline[-1]['participantFrames']
    else:
        lineMatch = matchtimeline[12]['participantFrames']
    
    team={} # {자리id : partic_id}
    
    line_match={} # {par_id:{}, 2:{}, 3:{}}

    for i in range(1,11):
        par_id = lineMatch[str(i)]['participantId']
        line_match[par_id] = lineMatch[str(i)]
        
        team[lane[par_id]] = par_id
        

    len_time = min(12, len(matchtimeline)-1)
    
    kills={}
    death={}
    for i in range(0,11):
        kills[i]=0
        death[i]=0
    
    for i in range(1, len_time+1):
        for event in matchtimeline[i]['events']:
            if event['type'] == "CHAMPION_KILL":
                if len(event['assistingParticipantIds']) ==0:
                    kills[event['killerId']] += 1.2
                else:
                    kills[event['killerId']] += 1
                
                kills[event['victimId']] -= 1
                for ast in event['assistingParticipantIds']:
                    kills[ast] += 0.8

   

    # top
    top1 = line_match[team[1]]
    top2 = line_match[team[6]]
    top1_gold = top1['totalGold']
    top2_gold = top2['totalGold']
    top1_level = top1['level']
    top2_level = top2['level']
    top1_kd = kills[team[1]]
    top2_kd = kills[team[6]]

    # mid
    mid1 = line_match[team[3]]
    mid2 = line_match[team[8]]
    mid1_gold = mid1['totalGold']
    mid2_gold = mid2['totalGold']
    mid1_level = mid1['level']
    mid2_level = mid2['level']
    mid1_kd = kills[team[3]]
    mid2_kd = kills[team[8]]

    # jungle
    jg1 = line_match[team[2]]
    jg2 = line_match[team[7]]
    jg1_gold = jg1['totalGold']
    jg2_gold = jg2['totalGold']
    jg1_level = jg1['level']
    jg2_level = jg2['level']
    jg1_kd = kills[team[2]]
    jg2_kd = kills[team[7]]

    # bot
    bot1 = line_match[team[4]]
    bot2 = line_match[team[9]]
    bot1_gold = bot1['totalGold']
    bot2_gold = bot2['totalGold']
    bot1_level = bot1['level']
    bot2_level = bot2['level']
    bot1_kd = kills[team[4]]
    bot2_kd = kills[team[9]]

    # supp
    supp1 = line_match[team[5]]
    supp2 = line_match[team[10]]
    supp1_gold = supp1['totalGold']
    supp2_gold = supp2['totalGold']
    supp1_level = supp1['level']
    supp2_level = supp2['level']
    supp1_kd = kills[team[5]]
    supp2_kd = kills[team[10]]


    score = []
    top1_line = (top1_kd*5 + 50) + goldScore(top1_gold, top2_gold)[0] + levScore(top1_level, top2_level)[0]
    top2_line = (top2_kd*5 + 50) + goldScore(top1_gold, top2_gold)[1] + levScore(top2_level, top2_level)[1]
    mid1_line = (mid1_kd*5 + 50) + goldScore(mid1_gold, mid2_gold)[0] + levScore(mid1_level, mid2_level)[0]
    mid2_line = (mid2_kd*5 + 50) + goldScore(mid1_gold, mid2_gold)[1] + levScore(mid1_level, mid2_level)[1]
    jg1_line = (jg1_kd*5 + 50) + goldScore(jg1_gold, jg2_gold)[0] + levScore(jg1_level, jg2_level)[0]
    jg2_line = (jg2_kd*5 + 50) + goldScore(jg1_gold, jg2_gold)[1] + levScore(jg1_level, jg2_level)[1]
    bot1_line = (bot1_kd*5 + 50) + goldScore(bot1_gold, bot2_gold)[0] + levScore(bot1_level, bot2_level)[0]
    bot2_line = (bot2_kd*5 + 50) + goldScore(bot1_gold, bot2_gold)[1] + levScore(bot1_level, bot2_level)[1]
    supp1_line = (supp1_kd*5 +50) + goldScore(supp1_gold, supp2_gold)[0] + levScore(supp1_level, supp2_level)[0]
    supp2_line = (supp2_kd*5 +50) + goldScore(supp1_gold, supp2_gold)[1] + levScore(supp1_level, supp2_level)[1]
    score.append(top1_line)
    score.append(top2_line)
    score.append(mid1_line)
    score.append(mid2_line)
    score.append(jg1_line)
    score.append(jg2_line)
    score.append(bot1_line)
    score.append(bot2_line)
    score.append(supp1_line)
    score.append(supp2_line)
    score.sort(reverse=True)
    result ={}
    result2= {}
    result[1] = score.index(top1_line) +1
    result[2] = score.index(jg1_line) +1
    result[3] = score.index(mid1_line) +1
    result[4] = score.index(bot1_line) +1
    result[5] = score.index(supp1_line) +1
    result2[6] = score.index(top2_line) +1
    result2[7] = score.index(jg2_line) +1
    result2[8] = score.index(mid2_line) +1
    result2[9] = score.index(bot2_line) +1
    result2[10] = score.index(supp2_line) +1
    
    team1_shit = max(result)
    team2_shit = max(result2)
    result.update(result2)
    return result, team1_shit, team2_shit

    





    
    

def goldScore(a,b):
    
    if a <= b:
        if a *1.2 >= b:
            return [50,50]
        elif a*1.3 >= b:
            return [45,55]
        elif a*1.4 >= b:
            return [40,60]
        elif a*1.5 >= b:
            return [35,65]
        else:
            return [30,70]
    
    else:
        if b *1.2 >= a:
            return [50,50]
        elif b*1.3 >= a:
            return [55,45]
        elif b*1.4 >= a:
            return [60,40]
        elif b*1.5 >= a:
            return [65,35]
        else:
            return [70,30]


def levScore(a,b):
    if a <= b:
        if a + 1 >= b:
            return [45,55]
        elif a + 2 >= b:
            return [40,60]
        elif a + 3 >= b:
            return [35,65]
        else:
            return [30,70]
    
    else:
        if b + 1 >= a:
            return [55,45]
        elif b + 2 >= a:
            return [60,40]
        elif b + 3 >= a:
            return [65,35]
        else:
            return [70,30]



def laneToPos(lane):
    p = {'top':1, 'jungle':2, 'mid':3, 'bot':4, 'supp':5}
    pos1={}
    nak=[]
    for i in range(1,6):
        if p[lane[i]] not in pos1.values():
            pos1[i] = p[lane[i]]
        else:
            nak.append(i)
    
    for n in nak:
        for i in range(1,6):
            if i not in pos1.values():
                pos1[n] = i
                break
    pos2={}
    nak=[]
    for i in range(6,11):
        if p[lane[i]]+5 not in pos2.values():
            pos2[i] = p[lane[i]]+5
        else:
            nak.append(i)
    
    for n in nak:
        for i in range(6,11):
            if i not in pos2.values():
                pos2[n] = i
                break
    pos1.update(pos2)
    return pos1



