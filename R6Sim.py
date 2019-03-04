import discord, aiohttp, asyncio, os, sys, time, logging, json, random, copy
from discord.ext import commands
from discord.ext.commands import Bot

'''
Optional
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
'''

#Variable globals
killPoints = 10
objPoints = 30
subObjPoints = 15
bot_prefix = "#"

gamemode_list = ["bomb", "hostage", "secure"]
killGadgets = ["Impact Grenade", "Claymore", "Frag Grenade", "Nitro Cell", "Breach Charge"]
updateList = ["prefix", "timer", "channellist", "permlist"]

clientID = open("Config/ClientID.txt", "r").read()
channelID = open("Config/ChannelID.txt", "r").readlines()
for channel in range(0, len(channelID)):
    channelID[channel] = channelID[channel].strip("\n")
OpList = "OpList.txt"
with open(OpList) as file:
    OpList = json.loads(str(file.read().replace("\n", "")))
    operatorNameList = list(OpList.keys())
    file.close()

Client = discord.Client()
client = commands.Bot(command_prefix=bot_prefix)

class ServerGenerator:
    def __init__(self, serverID, channelList, ID, name, owner, permissionList, prefix, timer):
        self.serverID = serverID
        self.channelList = channelList
        self.ID = ID
        self.name = name
        self.owner = owner
        self.permissionList = permissionList
        self.prefix = prefix
        self.timer = timer
        serverList["servers"][serverID] = {"object" : self}
        for channels in self.channelList:
            serverList["servers"][serverID]["channelList"] = {channels : ChannelGenerator(self.ID, clientID)}

class ChannelGenerator:
    def __init__(self, channelID, clientID):
        self.matchList = []
        self.maxLobbySize = 10
        self.clientID = clientID
        self.channelID = channelID
        self.matchLive = False
        self.matchLobby = False
    def returnObject(self):
        return self

class MatchGenerator:
    def __init__(self, gamemode, fromChannel):
        serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id].matchLobby = True
        self.winner = ""
        self.lobbySize = 0
        self.roundAlive = True
        self.gamemode = gamemode
        self.chosenOps = []
        self.aliveList = []
        self.playerList = []
        self.loadoutList = []
        self.teams = {}
        self.matchTeams = {}
        self.aliveTeams = {}
        self.rounds = {"team A": 0, "team B": 0}
        self.scoreboard = {"team A": {}, "team B": {}}
        self.objective = {"status": "clear", "defending": [], "attacking": [], "rolls" : 4}
        self.matchID = len(serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id].matchList) + 1
        serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id].matchList.append(self)

class PlayerGenerator:
    def __init__(self, playerName, operator, fromChannel, ID):
        currentMatch = serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id]
        currentMatch = currentMatch.matchList[len(currentMatch.matchList)-1]
        self.ID = ID
        self.loadout = []
        self.objective = False
        self.playerName = playerName
        self.operator = OpList[operator]
        self.team = ""
        self.side = ""
        currentMatch.playerList.append(self)
        currentMatch.aliveList.append(self)
        currentMatch.chosenOps.append(self.operator["name"])
        currentMatch.lobbySize += 1

class LoadoutGenerator:
    def __init__(self, currentMatch, fromChannel):
        currentMatch = currentMatch.matchList[len(currentMatch.matchList)-1]
        for players in range(0, currentMatch.lobbySize):
            operator = currentMatch.playerList[players].operator
            self.generate(operator, players, currentMatch)
    def generate(self, operator, index, currentMatch):
        loadoutList = []
        primaryList = self.delNA(list([operator['prim1'], operator["prim2"], operator["prim3"]]))
        if len(primaryList) < 2:
            loadoutList += [primaryList[0]]
        else:
            loadoutList += [primaryList[random.randint(0,len(primaryList)-1)]]
        secondaryList = self.delNA(list([operator['sec1'], operator['sec2']]))
        if len(secondaryList) < 2:
            loadoutList += [secondaryList[0]]
        else:
            loadoutList += [secondaryList[random.randint(0,len(secondaryList)-1)]]
        gadgetList = list([operator['gadget1'], operator['gadget2']])
        loadoutList += [gadgetList[random.randint(0,1)]]
        loadoutList += [currentMatch.playerList[index].operator["ungadget"]]
        loadoutList += [currentMatch.playerList[index].operator["ungadgettype"]]
        loadoutList += [currentMatch.playerList[index].operator["ungadgetspec"]]
        currentMatch.loadoutList += [loadoutList]
        currentMatch.playerList[index].loadout = loadoutList
    def delNA(self, List):
        NACount = 0
        for weapon in range(0, len(List)):
            if List[weapon] == "NA":
                NACount += 1
        for na in range(0, NACount):
            del List[List.index("NA")]
        return List

class TeamGenerator:
    #Dumb team generator, not happy about this one but it works
    def __init__(self, currentMatch, fromChannel):
        self.generate(currentMatch, fromChannel)
    def generate(self, currentMatch, fromChannel):
        teamList = {"team A":{}, "team B":{}}
        currentMatch = currentMatch.matchList[len(currentMatch.matchList)-1]
        scoreboard = copy.deepcopy(teamList)
        dif = 0
        if random.randint(1,2) == 1:
            teamList["team A"]["side"] = "attacking"
            teamList["team B"]["side"] = "defending"
        else:
            teamList["team A"]["side"] = "defending"
            teamList["team B"]["side"] = "attacking"
        for players in range(0, len(currentMatch.playerList)):
            rand = random.randint(0, 1)
            finalTeam = ""
            if rand == 0:
                teamList["team A"][currentMatch.playerList[players]] = currentMatch.playerList[players].operator["name"]
                finalTeam = "team A"
            elif rand == 1:
                teamList["team B"][currentMatch.playerList[players]] = currentMatch.playerList[players].operator["name"]
                finalTeam = "team B"
            dif = len(teamList["team A"]) - len(teamList["team B"])
            if dif >= 2:
                teamList["team A"].pop(currentMatch.playerList[players], None)
                teamList["team B"][currentMatch.playerList[players]] = currentMatch.playerList[players].operator["name"]
                finalTeam = "team B"
            elif dif <= -2:
                teamList["team B"].pop(currentMatch.playerList[players], None)
                teamList["team A"][currentMatch.playerList[players]] = currentMatch.playerList[players].operator["name"]
                finalTeam = "team A"
            currentMatch.playerList[players].team = finalTeam
            currentMatch.playerList[players].side = teamList[finalTeam]["side"]
        currentMatch.teams = copy.deepcopy(teamList)
        teamList["team A"].pop("side", None)
        teamList["team B"].pop("side", None)
        currentMatch.matchTeams = copy.deepcopy(teamList)
        currentMatch.aliveTeams = copy.deepcopy(teamList)
        currentMatch.scoreboard = scoreboard
        currentMatch.scoreboard["team A"]["score"] = 0
        currentMatch.scoreboard["team B"]["score"] = 0
        print(currentMatch.teams)
        print(currentMatch.matchTeams)
        print(currentMatch.aliveTeams)
        for player in currentMatch.playerList:
            currentMatch.scoreboard[player.team][player.playerName] = [[0,0], 0, 0]

@client.event
async def on_ready():
    message = "Bot Woke"
    print(message)

@client.event
async def MatchMain(currentMatch, fromChannel):
    currentMatch = currentMatch.matchList[len(currentMatch.matchList)-1]
    currentMatch.roundAlive = True
    currentRoll = True
    roundOver = False
    roundDif = 0
    roundCount = 1
    pW = ""
    chanceRatio = [
    #1% chance meta
    [0,1,"MatchMeta(currentMatch, fromChannel, selectedIndex)"],
    #Chance rare interaction
    [1,2,"MatchRare(currentMatch, fromChannel, selectedIndex)"],
    #Chance outside
    [2,3,"MatchOutside(currentMatch, fromChannel, selectedIndex)"],
    #Chance gadget kill
    [3,12,"MatchKill(currentMatch, fromChannel, selectedIndex, 'GK')"],
    #Chance unique gadget kill
    [12,18,"MatchKill(currentMatch, fromChannel, selectedIndex, 'UGK')"],
    #Chance suicide (done)
    [18,22,"MatchSuicide(currentMatch, fromChannel, selectedIndex)"],
    #Chance objective played
    [22, 40,"MatchOBJ(currentMatch, fromChannel, selectedIndex)"],
    #Chance kill, roll for how many kills
    [40,100,"MatchKill(currentMatch, fromChannel, selectedIndex)"]
    ]
    #Yeah the whole while True stuff seems stupid but it seems to be more consistent than other 'techniques'
    while True:
    #Match loop
        await asyncio.sleep(1)
        roundMessage = "**```ROUND: " + str(roundCount) + "```\n**"
        await send(roundMessage, fromChannel)
        while True:
        #Round loop
            await asyncio.sleep(1)
            while currentRoll:
                #Action loop
                selectedIndex = await MatchRoll(0, len(currentMatch.aliveList)-1)
                execFunction = await MatchFindRatio(4, 100, chanceRatio)
                currentRoll = await eval(execFunction)
            await send("**\n**", fromChannel)
            if currentMatch.objective["status"] == "securing" or currentMatch.objective["status"] == "planted":
                currentMatch.objective["rolls"] -= 1
            roundOver, roundWinners = await MatchTry(currentMatch, fromChannel)
            if roundOver:
                break
            else:
                currentRoll = True
        roundCount += 1
        roundDif = currentMatch.rounds["team A"] - currentMatch.rounds["team B"]
        currentMatch.rounds[roundWinners] += 1
        currentMatch.scoreboard[roundWinners]["score"] += 1
        #Match win conditions
        if currentMatch.rounds["team A"] == 3 and currentMatch.rounds["team B"] == 3:
            OT = True
        else:
            OT = False
        if currentMatch.rounds[roundWinners] == 4 and not OT:
            break
        elif currentMatch.rounds[roundWinners] == 5 and OT:
            break 
        outMsg = str("```" + roundWinners.upper() + " WIN THE ROUND```")
        await send(outMsg, fromChannel)
        await MatchScoreboard(currentMatch, fromChannel, "```--SCOREBOARD--\n\n")
        await MatchRoundReset(currentMatch, fromChannel)
        roundOver = False
        currentRoll = True
        pW = roundWinners
        await asyncio.sleep(1)
        continue
    currentMatch.winner = roundWinners
    await MatchOver(currentMatch, fromChannel, roundWinners)
    return

@client.event
async def MatchOver(currentMatch, fromChannel, matchWinners):
    print("Match Over")
    matchOverMessage = "```   \n    MATCH OVER\n--==" + matchWinners.upper() + " WIN==--\n  ```\n"
    await send(matchOverMessage, fromChannel)
    await MatchScoreboard(currentMatch, fromChannel, "```==FINAL SCOREBOARD==\n\n")
    serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id].matchLobby = False
    serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id].matchLive = False

@client.event
async def MatchScoreboard(currentMatch, fromChannel, addon):
    teamA = ""
    teamB = ""
    sortedA = []
    sortedB = []
    for x in currentMatch.playerList:
        score = currentMatch.scoreboard[x.team][x.playerName]
        if x.team == "team A":
            sortedA += [[score[0][1], x]]
        else:
            sortedB += [[score[0][1], x]]
    sortedA = await MatchQuicksort(sortedA)
    sortedB = await MatchQuicksort(sortedB)
    for x in sortedA:
        x = x[1]
        team = currentMatch.scoreboard["team A"]
        teamA += str(x.playerName + "'s Score: " + str(int(team[x.playerName][0][1]) + int(team[x.playerName][2])) + " K/D " +
        str(team[x.playerName][0][0]) + " : " + str(team[x.playerName][1])+"\n") 
    for x in sortedB:
        x = x[1]
        team = currentMatch.scoreboard["team B"]
        teamB += str(x.playerName + "'s Score: " + str(int(team[x.playerName][0][1]) + int(team[x.playerName][2])) + " K/D " +
        str(team[x.playerName][0][0]) + " : " + str(team[x.playerName][1])+"\n") 
    scoreboardMessage = (addon + "TEAM A (" + str(currentMatch.scoreboard["team A"]["score"]) + " ROUNDS WON):\n" + teamA +
    "TEAM B (" + str(currentMatch.scoreboard["team B"]["score"])+ " ROUNDS WON):\n" + teamB + "```")
    await send(scoreboardMessage, fromChannel)

@client.event
async def MatchTry(currentMatch, fromChannel):
    #Check if round could be over
    if currentMatch.teams["team A"]["side"] == "attacking":
        attackers = "team A"
        defenders = "team B"
    else:
        attackers = "team B"
        defenders = "team A"
    if len(currentMatch.aliveTeams[attackers]) == 0 or len(currentMatch.aliveTeams[defenders]) == 0:
        if len(currentMatch.aliveTeams[attackers]) >= 1:
            return True, attackers
        elif len(currentMatch.aliveTeams[defenders]) >= 1:
            if currentMatch.objective["status"] == "planted" or currentMatch.objective["status"] == "securing":
                if currentMatch.objective["rolls"] == 1:
                    await send(attackers + " successfully deployed the bomb")
                    return True, attackers
                else:
                    #Find a random defender to win
                    while True:
                        sigPlayer = currentMatch.aliveList[await MatchRoll(0, len(currentMatch.aliveList)-1)]
                        if sigPlayer.team == defenders:
                            break
                        else:
                            pass
                    defDef = list(currentMatch.aliveTeams[defenders].keys())[list(currentMatch.aliveTeams[defenders].values()).index(sigPlayer.operator["name"])]
                    if currentMatch.gamemode == "bomb":
                        winMessage = defDef.playerName + " successfully defused the bomb"
                    else:
                        winMessage = "Hostage is no longer secure"
                    currentMatch.scoreboard[defDef.team][defDef.playerName][2] += objPoints
                    await send(winMessage, fromChannel)
                    return True, defenders
            else:
                return True, defenders
    elif currentMatch.objective["rolls"] <= 0:
        return True, attackers
    elif currentMatch.objective["status"] == "defused":
        return True, defenders
    return False, None

@client.event
async def MatchQuicksort(team):
    less = []
    equal = []
    greater = []
    if len(team) > 1:
        pivot = team[0][0]
        for x in team:
            if x[0] < pivot:
                less.append(x)
            if x[0] == pivot:
                equal.append(x)
            if x[0] > pivot:
                greater.append(x)
        return await MatchQuicksort(less) + equal + await MatchQuicksort(greater)
    else:
        return team

@client.event
async def MatchRoundReset(currentMatch, fromChannel):
    currentMatch.aliveList = copy.deepcopy(currentMatch.playerList)
    currentMatch.roundAlive = True
    currentMatch.aliveTeams = copy.deepcopy(currentMatch.matchTeams)
    currentMatch.objective = {"status": "clear", "defending": [], "attacking": [], "rolls" : 4}
    for player in currentMatch.playerList:
        player.objective = False

@client.event
async def MatchFindRatio(rollRange1, rollRange2, chanceRatio):
    #Tests if roll within given list
    Return = None
    while Return == None:
        roll = await MatchRoll(rollRange1, rollRange2)
        for x in range(0, len(chanceRatio)):
            if roll in range(chanceRatio[x][0], chanceRatio[x][1]+1):
                Return = chanceRatio[x][2]
                return Return
    
@client.event
async def MatchKill(currentMatch, fromChannel, selectedIndex, *gadget):
    global killGadgets, killPoints, objPoints
    killRatio = [
    #Chance for 1 kill
    [0, 70, 1],
    #Chance 2 kills
    [70, 85, 2],
    #Chance 3 kills
    [85, 95, 3],
    #Chance 4 kills
    [95, 99, 4],
    #Chance 5 kills
    [99, 100, 5]
    ]
    killAmmount = await MatchFindRatio(0, 100, killRatio)
    print("Rolled " + str(killAmmount) + " kill (" + str(fromChannel.server) + ")" + str(currentMatch.aliveList[selectedIndex].playerName))
    sigPlayer = currentMatch.aliveList[selectedIndex]
    sigTeam = sigPlayer.team
    allNames = []
    for x in currentMatch.aliveList:
        allNames += [x.playerName]
    rollAmmount = (0,1)
    deathMessage = "killed"
    #If gadget is passed through, check if user loadout has a lethal gadget
    #Roll ammount is which loadout index is chosen, if no gadget roll between primary and secondary
    try:
        if gadget[0] == "GK":
            if sigPlayer.loadout[2] in killGadgets:
                rollAmmount = (2,2)
            else:
                return True
        elif gadget[0] == "UGK":
            if sigPlayer.loadout[4] == "kill":
                rollAmmount = (3,3)
                deathMessage = sigPlayer.loadout[5]
            else:
                return True
    except IndexError:
        pass
    if sigTeam == "team A":
        targetTeam = "team B"
    else:
        targetTeam = "team A"
    if currentMatch.gamemode == "hostage" and currentMatch.objective["status"] == "securing" and sigPlayer.side == "attacking":
        rollAmmount = (1,1)
    #If kill ammount is more than all alive, kill all
    if killAmmount >= len(currentMatch.aliveTeams[targetTeam]):
        popList = []
        for keys in currentMatch.aliveTeams[targetTeam]:
            popList += [keys]
        for enemy in popList:
            weapon = sigPlayer.loadout[await MatchRoll(rollAmmount[0], rollAmmount[1])]
            action = (sigPlayer.playerName + " (" + sigPlayer.operator["name"] +
            ") " + deathMessage + " " + enemy.playerName + " (" + enemy.operator["name"] +
            ") with their " + sigPlayer.loadout[await MatchRoll(rollAmmount[0], rollAmmount[1])])
            print(action + " (" + str(fromChannel.server) + ")")
            currentMatch.aliveTeams[targetTeam].pop(enemy, None)
            for x in range(0, len(currentMatch.aliveList)):
                if currentMatch.aliveList[x].playerName == enemy.playerName:
                    currentMatch.aliveList.pop(x)
                    break
            currentMatch.scoreboard[sigTeam][sigPlayer.playerName][0][0] += 1
            currentMatch.scoreboard[sigTeam][sigPlayer.playerName][0][1] += killPoints
            currentMatch.scoreboard[targetTeam][enemy.playerName][1] += 1
            await send(action, fromChannel)
        return False
    #Else kill however many rolled
    elif killAmmount < len(currentMatch.aliveTeams[targetTeam]):
        for enemies in range(0, killAmmount):
            spn = sigPlayer.playerName
            tpn = spn
            while tpn == spn:
                while True:
                    targetList = currentMatch.aliveTeams[targetTeam]
                    targetPlayer = currentMatch.aliveList[await MatchRoll(0, len(currentMatch.aliveList)-1)]
                    if targetPlayer in targetList:
                        break
                tpn = targetPlayer.playerName
                currentMatch.aliveTeams[targetTeam].pop(targetPlayer, None)
                currentMatch.aliveList.pop(allNames.index(enemy.playerName))
            currentMatch.scoreboard[sigTeam][sigPlayer.playerName][0][0] += 1
            currentMatch.scoreboard[sigTeam][sigPlayer.playerName][0][1] += killPoints
            currentMatch.scoreboard[targetPlayer.team][targetPlayer.playerName][1] += 1
            action = (sigPlayer.playerName + " (" + sigPlayer.operator["name"] +
            ") " + deathMessage + " " + targetPlayer.playerName + " (" + targetPlayer.operator["name"] +
            ") with their " + sigPlayer.loadout[await MatchRoll(rollAmmount[0], rollAmmount[1])])
            print(action + " (" + str(fromChannel.server) + ")")
            await send(action, fromChannel)
        return False
    else:
        return True

@client.event
async def MatchRoll(a, b):
    return random.randint(a, b)

@client.event
async def MatchMeta(self):
    pass

@client.event
async def MatchRare(self):
    pass

@client.event
async def MatchOutside(self):
    pass

@client.event
async def MatchSuicide(currentMatch, fromChannel, selectedIndex):
    global killGadgets, killPoints, objPoints
    sigPlayer = currentMatch.aliveList[selectedIndex]
    allNames = []
    for x in currentMatch.aliveList:
        allNames += [x.playerName]
    suicideMessage = " died from fall damage"
    #Test if user can blow themself up then roll for it
    if sigPlayer.loadout[2] in killGadgets:
        if await MatchRoll(0,2) == 1:
            suicideMessage = " blew themself up with their " + sigPlayer.loadout[2].lower()
    action = (sigPlayer.playerName + suicideMessage)
    currentMatch.scoreboard[sigPlayer.team][sigPlayer.playerName][1] += 1
    teamKey = list(currentMatch.aliveTeams[sigPlayer.team].keys())[list(currentMatch.aliveTeams[sigPlayer.team].values()).index(sigPlayer.operator["name"])]
    currentMatch.aliveTeams[sigPlayer.team].pop(teamKey, None)
    currentMatch.aliveList.pop(allNames.index(sigPlayer.playerName))
    print(action + " (" + str(fromChannel.server) + ")")
    await send(action, fromChannel)
    return False

@client.event
async def MatchOBJ(currentMatch, fromChannel, selectedIndex):
    global killPoints, objPoints
    sigPlayer = currentMatch.aliveList[selectedIndex]
    sigSide = sigPlayer.side
    sigTeam = sigPlayer.team
    currentOBJ = currentMatch.objective
    print(sigPlayer.playerName + sigSide + sigTeam)
    #Testing for possible status'
    #return True will reroll as the roll would not have any impact which is unfair
    if sigSide == "attacking":
        if sigPlayer in currentOBJ["attacking"]:
            return True
        elif currentMatch.gamemode == "bomb":
            if len(currentOBJ["attacking"]) == 1:
                return True
            else:
                currentOBJ["attacking"] += [sigPlayer]
                currentMatch.scoreboard[sigTeam][sigPlayer.playerName][2] += subObjPoints
                action = (sigPlayer.playerName + " has planted the bomb")
                currentOBJ["status"] = "planted"
                await send(action, fromChannel)
        elif currentMatch.gamemode == "secure":
            currentOBJ["attacking"] += [sigPlayer]
            if len(currentOBJ["defending"]) > len(currentOBJ["attacking"]):
                pass
            elif len(currentOBJ["defending"]) == len(currentOBJ["attacking"]):
                currentOBJ["status"] = "contesting"
                action = (sigPlayer.playerName + " is contesting the objective")
                await send(action, fromChannel)
            elif len(currentOBJ["defending"]) < len(currentOBJ["attacking"]):
                currentOBJ["status"] = "securing"
                currentMatch.scoreboard[sigTeam][sigPlayer.playerName][2] += subObjPoints
                action = (sigPlayer.playerName + " is securing the objective")
                await send(action, fromChannel)
        elif currentMatch.gamemode == "hostage":
            if currentOBJ["status"] == "securing":
                return True
            elif currentOBJ["status"] == "clear":
                currentOBJ["status"] = "securing"
                currentOBJ["attacking"] += [sigPlayer]
                currentMatch.scoreboard[sigTeam][sigPlayer.playerName][2] += subObjPoints
                action = (sigPlayer.playerName + " is securing the hostage")
                await send(action, fromChannel)
    elif sigSide == "defending":
        if sigPlayer in currentMatch.objective["defending"]:
            return True
        elif currentMatch.gamemode == "bomb":
            if currentOBJ["status"] == "planted":
                currentMatch.scoreboard[sigTeam][sigPlayer.playerName][2] += objPoints
                action = (sigPlayer.playerName + " defused the bomb")
                currentOBJ["status"] = "defused"
                await send(action, fromChannel)
            elif currentOBJ["status"] == "clear":
                return True
        elif currentMatch.gamemode == "secure":
            currentOBJ["defending"] += [sigPlayer]
            if len(currentOBJ["defending"]) > len(currentOBJ["attacking"]):
                return True         
            elif len(currentOBJ["defending"]) == len(currentOBJ["attacking"]):
                currentOBJ["status"] = "contesting"
                action = (sigPlayer.playerName + " is contesting the objective")
                await send(action, fromChannel)
            elif len(currentOBJ["defending"]) < len(currentOBJ["attacking"]):
                pass
        elif currentMatch.gamemode == "hostage":
            if currentOBJ["status"] == "securing":
                if await MatchRoll(1, 3) == 1:
                    targetPlayer = currentOBJ["attacking"][0]
                    currentOBJ["status"] = "clear"
                    action = (sigPlayer.playerName + " (" + sigPlayer.operator["name"] +
                    ") killed " + targetPlayer.playerName + " (" + targetPlayer.operator["name"] +
                    ") with their " + sigPlayer.loadout[await MatchRoll(0,1)])
                    print(action + " (" + str(fromChannel.server) + ")")
                    currentOBJ["attacking"] = []
                    for x in range(0, len(currentMatch.aliveList)):
                        if currentMatch.aliveList[x].playerName == targetPlayer.playerName:
                            currentMatch.aliveList.pop(x)
                            break
                    teamKey = list(currentMatch.aliveTeams[sigPlayer.team].keys())[list(currentMatch.aliveTeams[sigPlayer.team].values()).index(sigPlayer.operator["name"])]
                    currentMatch.aliveTeams[sigPlayer.team].pop(teamKey, None)
                    currentMatch.scoreboard[sigTeam][sigPlayer.playerName][0][0] += 1
                    currentMatch.scoreboard[sigTeam][sigPlayer.playerName][0][1] += killPoints
                    currentMatch.scoreboard[sigTeam][sigPlayer.playerName][2][0] += 1
                    currentMatch.scoreboard[sigTeam][sigPlayer.playerName][2] += objPoints
                    currentMatch.scoreboard[targetPlayer.team][targetPlayer.playerName][1] += 1
                    await send(action, fromChannel)
                    await send("Hostage is no longer secure", fromChannel)
                else:
                    return True
            elif currentOBJ["status"] == "clear":
                return True
    return False

@client.event
async def send(message, fromChannel):
    #Shortening the function, for my sanity
    await client.send_message(fromChannel, message)

@client.event
async def start_countdown(fromChannel):
    timer = serverList["servers"][fromChannel.server.id]["object"].timer
    print("Beginning countdown " + str(timer) + " (" + str(fromChannel.server) + ")")
    currentMatch = serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id]
    #Countdown
    while currentMatch.matchLobby and timer > 0:
        if timer == 60 or timer == 30 or timer == 10 or timer == 3 or timer == 2 or timer == 1:
            await send("**`" + str(timer) + "`**` seconds left to join`", fromChannel)
        await asyncio.sleep(1)
        timer -= 1
    #If match is full
    if currentMatch.matchList[len(currentMatch.matchList)-1].lobbySize < 2:
        await send("*`Not enough players to start lobby`*", fromChannel)
        currentMatch.matchLobby = False
        currentMatch.matchLive = False
    #If match not full
    else:
        currentMatch.matchLobby = False
        currentMatch.matchLive = True
        await send("**`==Beginning match==`**", fromChannel)
        await start_match(fromChannel, currentMatch)
        print("Match finished")
        currentMatch.matchList[len(currentMatch.matchList)-1] = [currentMatch.matchList[len(currentMatch.matchList)-1].winner]
        return

@client.event
async def callHelp(message, fromChannel):
    #Print help 
    await send("{0.author.mention} To start a match, enter '#match start [Bomb/Hostage/Secure]' to start one\n If you need help with setting up the bot, type #R6Sim".format(message), fromChannel)

@client.event
async def callStart(message, fromChannel):
    global gamemode_list
    selectedGamemode = message.content.replace("match start ", "").lower()
    print(serverList["servers"])
    currentMatch = serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id]
    #If no match
    if not currentMatch.matchLive and not currentMatch.matchLobby:
    #If entered gamemode exists
        if selectedGamemode in gamemode_list:
            currentMatch.currentMatch = MatchGenerator(selectedGamemode, fromChannel)
            print(message.server)
            print(str(selectedGamemode.title()) + " lobby started in " + str(fromChannel.id) + " (" + str(message.server) + ") Match ID: " + str(currentMatch.currentMatch.matchID))
            await send("{0.author.mention} has started a match, type #match join [Operator] to join the match".format(message), fromChannel)
            await start_countdown(fromChannel)
        else:
            await send("{0.author.mention} That gamemode is not recognised, please choose between Bomb, Hostage or Secure".format(message), fromChannel)
    #If match in progress
    elif currentMatch.matchLive:
        await send("{0.author.mention} A match is currently in progress, please wait until it finishes to join".format(message), fromChannel)
    #If match has room
    elif currentMatch.matchLobby and not currentMatch.matchLive:
        try:
            if currentMatch.matchList[len(currentMatch.matchList)-1].lobbySize < currentMatch.matchLobbySize:
                await send("{0.author.mention} The match you are trying to join is currently full".format(message), fromChannel)
            else:
                await send("{0.author.mention} A lobby is currently available, to join type '#match join [Operator]".format(message), fromChannel)
        except:
            await send("{0.author.mention} A lobby is currently available, to join type '#match join [Operator]".format(message), fromChannel)

@client.event
async def callJoin(message, fromChannel):
    global operatorNameList
    #If live match has room
    currentMatch = serverList["servers"][fromChannel.server.id]["channelList"][fromChannel.id]
    for players in currentMatch.matchList[len(currentMatch.matchList)-1].playerList:
        if message.author.id == players.ID:
            await send("{0.author.mention} You are already in the match, please allow it to finish".format(message), fromChannel)
            return
    if currentMatch.matchLobby and not currentMatch.matchLive and currentMatch.matchList[len(currentMatch.matchList)-1].lobbySize <  currentMatch.maxLobbySize:
        #Error catch
        opArg = message.content.replace("match join ", "").title()
        if opArg == "Iq":
            opArg = "IQ"
        #If OP in list (check for chosen ops)
        if opArg in operatorNameList and opArg not in currentMatch.matchList[len(currentMatch.matchList)-1].chosenOps:
            chosenOp = operatorNameList[operatorNameList.index(opArg)]
            print(str(message.author.display_name) + " joined as " + chosenOp + " (" + str(message.server) + ")")
            PlayerGenerator(str(message.author.display_name), chosenOp, fromChannel, message.author.id)
            await send(str(message.author.display_name) + " Joined as " + str(chosenOp), fromChannel)
            op = "mira"
            joinmsg = ("#match join " + op)
            await send((joinmsg), fromChannel)
        #If op chosen
        elif opArg in currentMatch.matchList[len(currentMatch.matchList)-1].chosenOps:
            await send(("{0.author.mention} " + opArg + " has already been chosen, please choose another operator").format(message), fromChannel)
        #If op doesn't exist
        elif opArg not in operatorNameList:
            await send("{0.author.mention} That operator doesn't exist, please choose an existing operator".format(message), fromChannel)
    #If match in progress
    elif currentMatch.matchLives:
        await send("{0.author.mention} A match is currently in progress, please wait until it finishes to join".format(message), fromChannel)
    #If no match
    elif not currentMatch.matchLive and not currentMatch.matchLobby:
        await send("{0.author.mention} A match is not currently in progress, type '#match start [Bomb/Hostage/Secure]' to start one".format(message), fromChannel)

@client.event
async def callServer(message, fromChannel):
    simMsg = message.content.replace("R6Sim ", "").lower()
    if simMsg == "init":
        if fromChannel.server.id not in serverList["servers"]:
            await initialise(fromChannel.server.id, fromChannel)
        else:
            await send("{0.author.mention} R6Sim has already been set up in this server".format(message), fromChannel)
    elif simMsg.startswith("update"):
        if str(message.author.id) in serverOBJ.permissionList:
            toUpdate = simMsg.replace("update ", "")
            toUpdateCommand = ""
            try:
                try:
                    for x in range(0, [toUpdate].index(" ")):
                        toUpdateCommand += toUpdate[x]
                        print(x)
                except:
                    toUpdate = toUpdateCommand
                if toUpdateCommand in updateList:
                    await serverUpdate(message, fromChannel, toUpdate)
                else:
                    await send("{0.author.mention} That command is not recognised, current supported commands are: R6Sim update [prefix, timer, channellist, permlist]".format(message), fromChannel)
            except Exception as e:
                print(e)
                await send("{0.author.mention} The current supported commands are: R6Sim update [prefix, timer, channellist, permlist]".format(message), fromChannel)
        else:
            await send("{0.author.mention} Only the owner and selected users have access to this command".format(message), fromChannel)
    elif fromServer not in serverList["servers"]:
        await send("{0.author.mention} R6Sim hasn't been set up in this server yet, use #R6Sim init to initialise the bot".format(message), fromChannel)
    else:
        if str(message.author.id) in serverOBJ.permissionList:
            await serverDisplay(message, fromChannel)
        else:
            await send("{0.author.mention} Only the owner and selected users have access to this command".format(message), fromChannel)

async def serverDisplay(message, fromChannel):
    server = serverList["servers"][fromChannel.server.id]["object"]
    with open("ServerList.txt") as file:
        ServerList = json.loads(str(file.read().replace("\n", "")+"}}"))
        file.close()
    sMsg = "```Current settings:\n\nChannel list:\n"
    for channels in server.channelList:
        sMsg += str(channels) + " (" + str(fromChannel.server.get_channel(channels).name) + ")\n"
    sMsg += "\nPermission list:\n"
    for users in server.permissionList:
        sMsg += str(users) + " (" + str(fromChannel.server.get_member(users).display_name) + ")\n"
    sMsg += "\nPrefix: " + str(server.prefix) + "\nTimer length: " + str(server.timer) + "```"
    await send(sMsg, fromChannel)

async def serverUpdate(message, fromChannel, toUpdate):
    pass

'''
On message
'''

@client.event
async def on_message(message):
    fromChannel = message.channel
    fromServer = fromChannel.server.id
    '''if message.author == client.user:
        return'''
    try:
        serverOBJ = serverList["servers"][fromChannel.server.id]["object"]
        prefix = serverOBJ.prefix
    except:
        prefix = "#"
    if message.content.startswith(prefix):
        message.content = message.content.replace(prefix, "")
        #If help
        if message.content.lower() == "help":
            await callHelp(message, fromChannel)
        #If match start
        elif message.content.startswith("match start"):
            await callStart(message, fromChannel)
        #Join match
        elif message.content.startswith("match join"):
            await callJoin(message, fromChannel)
        #Config
        elif message.content.startswith("R6Sim"):
            await callServer(message, fromChannel)
    else:
        return

@client.event
async def start_match(fromChannel, currentMatch):
    #Create loadouts for each player
    LoadoutGenerator(currentMatch, fromChannel)
    #Assign each player to teams
    TeamGenerator(currentMatch, fromChannel)
    #Display all players in each team
    teamA = ""
    teamB = ""
    for x in currentMatch.matchList[len(currentMatch.matchList)-1].matchTeams["team A"]:
        teamA += str(x.playerName) + "\n"
    for x in currentMatch.matchList[len(currentMatch.matchList)-1].matchTeams["team B"]:
        teamB += str(x.playerName) + "\n"
    teamMessage = (
        "```TEAM A:\n" +
        teamA + "---== VS ==---\n"+
        "TEAM B:\n" +
        teamB + "```")
    await send(teamMessage, fromChannel)
    await MatchMain(currentMatch, fromChannel)
    return

@client.event
async def initialise(server, fromChannel):
    try:
        with open("ServerList.txt") as file:
            ServerList = json.loads(str(file.read().replace("\n", "")+"}}"))
            print(len(serverList["servers"]))
            serverLen = len(serverList["servers"])
            file.close()
    except:
        serverLen = 0
    if serverLen == 0:
        toWrite = "{"
    else:
        toWrite = "},"
    toWrite += ('\n\t"ChannelID' + str(len(serverList["servers"])) + '" : {\n\t\t"server" : "' + str(fromChannel.server.id) + '",\n\t\t"name" : "' + str(fromChannel.server) +
        '",\n\t\t"channelList" :\n\t\t["' + str(fromChannel.id) + '"],\n\t\t"owner" : "' + str(fromChannel.server.owner.id) + '",\n\t\t"permissionList" :\n\t\t["' + 
        str(fromChannel.server.owner.id) + '"],\n\t\t"prefix" : "#",\n\t\t"timer" : 20')
    with open("ServerList.txt", "a") as file:
        file.write(toWrite)
        file.close()
    await tryOpen()
    await send("R6Sim online", fromChannel)

@client.event
async def tryOpen():
    try: 
        with open("ServerList.txt") as file:
            ServerList = json.loads(str(file.read().replace("\n", "")+"}}"))
            file.close()
        for x in range(len(serverList["servers"]), len(ServerList)):
            server = ServerList["ChannelID" + str(x)]
            ServerGenerator(server["server"], server["channelList"], x, server["name"], server["owner"], server["permissionList"], server["prefix"], server["timer"])
            print("Connected to " + server["name"])
    except:
        pass

serverList = {"servers":{}}
try: 
    with open("ServerList.txt") as file:
        ServerList = json.loads(str(file.read().replace("\n", "")+"}}"))
        file.close()
    for x in range(len(serverList["servers"]), len(ServerList)):
        server = ServerList["ChannelID" + str(x)]
        ServerGenerator(server["server"], server["channelList"], x, server["name"], server["owner"], server["permissionList"], server["prefix"], server["timer"])
        print("Connected to " + server["name"])
except:
    pass

client.run(clientID)
