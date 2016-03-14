import random, sys, math, numpy, copy
from collections import defaultdict

from base import *
import base


def fightscore(adv, thing):

    if not isinstance(thing, Monster):
        return 0

    return sum([adv.strat.fightcalc[val(adv, thing)[0]] * val(adv, thing)[1] for val in adv.strat.statlist])

def returnscore(thing, weight):

    if not isinstance(thing, Empty) or not thing.visited:
        return 0

    if weight == 0:
        return 0

    return weight / thing.visited


def run_strat(adv, floor):
    outcome_weights = {
        outcome : 0 for outcome in outcomes
        }
    
    for i in xrange(-VISION_RADIUS, VISION_RADIUS):
        for j in xrange(-VISION_RADIUS, VISION_RADIUS):
            gene = adv.strat[i,j]
            if not gene:
                continue
            thing = floor[adv.x + i][adv.y + j]
            weights = gene.weightmods[thing.__class__]
            for outcome in weights:
                outcome_weights[outcome] += weights[outcome]["base"] + weights[outcome]["fightweight"] * fightscore(adv, thing) +  returnscore(thing, weights[outcome]["visitedweight"])
    debug(str(outcome_weights))
    weights = []
    for i, outcome in enumerate(outcomes):
        weights.append(outcome_weights[outcome])


    m = min(weights)
    weights = map(lambda x: (x - m, 0)[x < 0], weights)

    debug(str(weights))
    return weightchoice(outcomes, weights)
    

def move(adv, outcome, floor):
    adv.x += outcome[0]
    adv.y += outcome[1]
    for rows in floor:
        for thing in rows:
            if isinstance(thing, Empty) and thing.visited is not None:
                thing.visited += 1
    

def run(adv, floor):

    debug(repr(floor))
    debug("===")
    while adv.hp > 0 and adv.nrg > 0 and not isinstance(floor[adv.x][adv.y], Stairs):


        adv.nrg -= 1
        adv.age += 1
        debug(repr(adv))
        debug("---")
        
        outcome = run_strat(adv, floor)
        debug(outcome)

        thing = floor[adv.x + outcome[0]][adv.y + outcome[1]]
            
        if isinstance(thing, Wall):
            debug("Bonk.")
            pass
        elif isinstance(thing, Empty):
            debug("Moving " + str(outcome))
            thing.visited = 0            
            move(adv, outcome, floor)
        elif isinstance(thing, Stairs):
            debug("Moving onto stairs!")
            move(adv, outcome, floor)
        elif isinstance(thing, Monster):
            debug("Fighting " + repr(thing))
            thing.hp -= adv.atk
            if thing.hp <= 0:
                floor[adv.x + outcome[0]][adv.y + outcome[1]] = Empty(1)
                adv.nrg += thing.nrg
                adv.meta += thing.meta
                debug("It died.")
            else:
                adv.hp -= thing.atk * (10 / (10 + adv.arm))
                debug("It hit me with " + str(thing.atk) + " and now I have " + str(adv.hp) + " hp.")
        elif isinstance(thing, Item):
            debug("Picking up item.")
            adv.pickup_item(thing)
            floor[adv.x + outcome[0]][adv.y + outcome[1]] = Empty(1)
            floor[adv.x + outcome[0]][adv.y + outcome[1]].visited = 0            
            move(adv, outcome, floor)
        elif isinstance(thing, Consumable):
            debug("Picking up consumable.")
            floor[adv.x + outcome[0]][adv.y + outcome[1]] = Empty(1)
            floor[adv.x + outcome[0]][adv.y + outcome[1]].visited = 0            
            thing.drink(adv)
            move(adv, outcome, floor)
        
                

# a = Adventurer.generate()
# f = Floor(1)
# run(a, f)

def mate_strats(p1, p2):

    score1, s1 = p1
    score2, s2 = p2    

    s = Strat()

    for i in xrange(-VISION_RADIUS, VISION_RADIUS):
        for j in xrange(-VISION_RADIUS, VISION_RADIUS):
            if s[i,j] is None:
                continue
            sample = numpy.random.beta(numpy.sqrt(score1), numpy.sqrt(score2))
            s[i,j] = mate_genes(s1[i,j], s2[i,j], sample)

    return s

def mate_genes(g1, g2, interpolant):

    g = Gene()
    for thing in g.weightmods:
        for outcome in outcomes:
            g.weightmods[thing][outcome] = {
                key : numpy.interp(interpolant, [0,1], [g2.weightmods[thing][outcome][key], g1.weightmods[thing][outcome][key]])
                for key in g.weightmods[thing][outcome]
                }
    return g


#simulate and generate fitness
def generation(strats, runs, fitness):
    sys.stdout.flush()
    scores = {s : [0, s] for s in strats}

    for strat in strats:
        for i in xrange(runs):
            cur = Adventurer.generate(strat)
            run(cur, Floor(1))
            scores[strat][0] += fitness(cur)
        scores[strat][0] /= float(runs)

    return scores

#stdev probably wants to be able to be a function of gen
#so that mutations get less extreme with time
def mutate(strat, stdev):

    ret = Strat(copy.deepcopy(strat.genes))
    for i in xrange(-VISION_RADIUS, VISION_RADIUS):
        for j in xrange(-VISION_RADIUS, VISION_RADIUS):
            if ret[i,j] is None:
                continue
            for thing in things:
                for outcome in outcomes:
                    ret[i,j].weightmods[thing][outcome] = {
                        key : ret[i,j].weightmods[thing][outcome][key] + numpy.random.normal(0, stdev)
                        for key in ret[i,j].weightmods[thing][outcome]
                        }


    return ret


def next_gen(scores, gen, sources):

    top = sorted(scores.values(), key=lambda x:x[0], reverse=True)

#    uncomment this to see how well it's learnng over time    
#    print "Generation ", gen, ": "
#    for score, thing in top:
#        print repr(thing)+": %.03f" % score
        
    nxt = []

    for i in xrange(sources["unchanged"]):
        nxt.append(top[i][1])

    for i in xrange(sources["mated"]):
        p1 = weightchoice(top, map(lambda x: x[0] * x[0] * x[0], top))
        p2 = weightchoice(top, map(lambda x: x[0] * x[0] * x[0], top))
        child = mate_strats(p1, p2)
        nxt.append(child)
    for i in xrange(sources["mutated"]):
        parent = weightchoice(top, map(lambda x: x[0] * x[0] * x[0], top))
        child = mutate(parent[1], sources["mutation_stdev"] / numpy.log(gen+1))
        
        nxt.append(child)
    for i in xrange(sources["random"]):
        child = Strat()
        nxt.append(child)
        
    return nxt
                
def trial(gens, runs, sources, fitness):
    gen = [Strat() for i in xrange(int(sum(sources.values())))]
    scores = None
    
    for i in xrange(gens):
        if scores:
            gen = next_gen(scores, i, sources)

        scores = generation(gen, runs, fitness)
        

    print "Final results:"
    o = sorted(scores.values(), key=lambda x:x[0], reverse=True)
    for (score, thing) in o[:5]:
        print str(score) + ": ", thing

#    uncomment these to run the winning individual with output at the end        
#    base.debug_on = True
#    run(Adventurer.generate(o[0][1]), Floor(1))

def default_fitness(adv):
    return adv.x + adv.y + sum(adv.stats.values())/10 + [0,4][adv.x == BOARD_SIZE and adv.y == BOARD_SIZE]


#replace the question marks with how many individuals of each type you'd like in each generaton. 

sources = {
    "unchanged" : ?,
    "mated" : ?,
    "mutated" : ?,
    "mutation_stdev" : ?, # probably pick a number between 0 and 2, or so.
    "random" : ?
}

#first two args are total generations, number of times to run an individual (fitness = avg fitness of results)
trial(?, ?, sources, default_fitness)


