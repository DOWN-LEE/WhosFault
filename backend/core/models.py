from django.db import models

# Create your models here.

'''
### Rank ###

unrank          0
iron            1~4
bronze          11 ~ 14
silver          21 ~ 24
gold            31 ~ 34
platinum        41 ~ 44
diamond         51 ~ 54
master          61
grandmaster     71
challenger      81
'''


class Summoner(models.Model):
    name = models.CharField(max_length=20, db_index=True)

    summonerId = models.CharField(max_length=100)
    accountId = models.CharField(max_length=100)
    puuid = models.CharField(max_length=100)

    profileIconId = models.SmallIntegerField()
    summonerLevel = models.SmallIntegerField()

    solo_rank = models.SmallIntegerField(default=0)
    solo_rank_win = models.SmallIntegerField(default=0)
    solo_rank_loss = models.SmallIntegerField(default=0)

    flex_rank = models.SmallIntegerField(default=0)
    flex_rank_win = models.SmallIntegerField(default=0)
    flex_rank_loss = models.SmallIntegerField(default=0)


class Match(models.Model):
    matchId = models.BigIntegerField()
    timestamp = models.BigIntegerField()
    gametype = models.CharField(max_length=5)

