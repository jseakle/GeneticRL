import uuid, random, sys

BOARD_SIZE = 12
VISION_RADIUS = 2

debug_on = False
def debug(x):
    if debug_on:
        print x
            
def constrain(x, amt, low, high):
    return min(high, max(low, x + amt))

def weightchoice(items, weights):

    cumulative = []
    prev = 0
    for i in weights:
        cumulative.append(i + prev)
        prev = cumulative[-1]
        

    r = random.uniform(0, cumulative[-1])

    for i, threshold in enumerate(cumulative):
        if r <= threshold:
            return items[i]


class Adventurer(object):

    stat_types = ["hp", "atk", "arm", "nrg", "meta"]

    def __getattr__(self, attr):
        if attr in self.stat_types:
            return self.stats[attr]
        return self.__dict__[attr]


    def __init__(self, strat, *args):
        self.x = 1
        self.y = 1
        self.item = None
        self.age = 0

        self.stats = {}
        for i, stat in enumerate(self.stat_types):
            self.stats[stat] = args[i]
        
        self.strat = strat

    def pickup_item(self, item):
        if self.item:
            self.drop_item()
        self.item = item
        self.atk += item.atk
        self.arm += item.arm

    def drop_item(self):
        self.atk -= self.item.atk
        self.arm -= self.item.arm
        self.item = None

    @staticmethod
    def generate(strat=None):
        vals = [2 for stat in Adventurer.stat_types]
        vals[-2] = 40
        vals[-1] = 0
        return Adventurer((strat, Strat())[strat is None], *vals)

    def __repr__(self):
        return "x: %d, y: %d, hp: %5f, atk: %5f, arm: %5f, nrg: %5f" % (self.x, self.y, self.hp, self.atk, self.arm, self.nrg)


things = []

def thing(cls):
    things.append(cls)
    return cls
        
@thing
class Wall(object):

    weight = 1
    
    def __init__(self, depth):
        pass

@thing
class Empty(object):

    weight = 3
    visited = None
    
    def __init__(self, depth):
        pass


@thing
class Monster(object):

    weight = 2.5
    
    stat_types = ["atk", "hp", "nrg", "meta"]

    def __getattr__(self, attr):
        if attr in self.stat_types:
            return self.stats[attr]
    
    def __init__(self, depth):

        self.stats = {
            "atk" : random.random() * depth,
            "hp" : random.random() * depth * 8,
            "nrg" : random.random() * depth * 3,
            "meta" : depth * random.randint(1,3)
            }

    def __repr__(self):
        ret = "Monster: "
        for stat in self.stat_types:
            ret += stat + ": " + str(getattr(self, stat)) + " "
        return ret
    

@thing
class Item(object):

    weight = 3

    def __init__(self, depth):

        self.atk = random.random() * depth
        self.arm = random.random() * depth

    def act(self):
        pass


@thing
class Consumable(object):

    weight = 3

    def __init__(self, depth):

        self.hp = random.random() * depth
        self.nrg = (random.random() * depth) 
        self.atk = (random.random() * depth) / 2
        self.arm = (random.random() * depth) / 2

    def drink(self, adv):
        for stat in adv.stats:
            if hasattr(self, stat):
                setattr(adv, stat, getattr(adv, stat) + getattr(self, stat))

@thing
class Stairs(object):
    weight = 0


thingweights = [thing.weight for thing in things]


outcomes = [(0,-1), (1,0), (0,1), (-1,0)]

class Gene(object):

    def __init__(self):
        
        self.weightmods = {
            thing : {
                outcome : { "base" : (random.random() - .5), "fightweight" : random.random(), "visitedweight" : random.random() - .5} for outcome in outcomes
                }
            for thing in things
            }

    def __repr__(self):
        ret = ""
        for outcome in outcomes:
            ret += str(outcome) + ": " + str(self.weightmods[Item][outcome]) + "\n"
        return ret
        
        
class Strat(object):

    def __getitem__(self, tup):

        x, y = tup
        
        return self.genes[x][y]

    def __setitem__(self, tup, val):

        x, y = tup

        self.genes[x][y] = val


    def __init__(self, genes = None):
        if genes is not None:
            self.genes = genes
        else:

            self.genes = []
            for i in xrange(-VISION_RADIUS, VISION_RADIUS):
                self.genes.append([])
                for j in xrange(-VISION_RADIUS, VISION_RADIUS):
                    if abs(i) + abs(j) <= VISION_RADIUS:
                        self.genes[-1].append(Gene())
                    else:
                        self.genes[-1].append(None)

        self.statlist = [
            (lambda klass, idx, statname: lambda a, b: (klass.__name__ + statname, (a, b)[idx].stats[statname]))(klass, idx, statname)

            for klass, idx in [(Adventurer, 0), (Monster, 1)]
            for statname in klass.stat_types
            ]
        self.fightcalc = {
            klass.__name__ + statname : random.random() for klass in [Adventurer, Monster] for statname in klass.stat_types
            }
            
            
        
class Floor(object):

    def __getitem__(self, i):
        return self.cells[i]

    def __init__(self, depth):

        self.cells = self.generate(depth)
        
    def generate(self, depth):

        board = [[(Wall(depth), self.gen_cell(depth))[i not in [0, BOARD_SIZE + 1] and j not in [0, BOARD_SIZE + 1]] for i in xrange(BOARD_SIZE + 2)] for j in xrange(BOARD_SIZE + 2)]
        board[BOARD_SIZE][BOARD_SIZE] = Stairs()
        return board

    def gen_cell(self, depth):

        return weightchoice(things, thingweights)(depth)

    def __repr__(self):
        ret = ""
        for i in self.cells:
            for j in i:
                ret += j.__class__.__name__[0]
            ret += "\n"
        return ret

