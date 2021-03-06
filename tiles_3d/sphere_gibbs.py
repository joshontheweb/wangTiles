import numpy as np
import time

from extract_tiles_vox import *
from potentials import *
from create_sphere import *
from display import *
from constants import *
import random

from pyvox.models import Vox
from pyvox.writer import VoxWriter

# np.random.seed(0)
fixup_budget = 100


spherehood_relative_array = []
for i in range(SPHERE_WIDTH):
    for j in range(SPHERE_WIDTH):
        for l in range(SPHERE_WIDTH):
            loc = (i - SPHERE_WIDTH / 2, j - SPHERE_WIDTH / 2, l - SPHERE_WIDTH / 2)
            if loc != (0, 0, 0):
                spherehood_relative_array.append(loc)
spherehood_relative_array = np.array(spherehood_relative_array)

def spherehood(i,j, l):
    hood = spherehood_relative_array + np.array([i,j, l])
    condition = np.logical_and(
                np.logical_and(
                hood[:,0] >= 0,
                hood[:,1] >= 0,
                hood[:,2] >= 0),
                np.logical_and(
                hood[:,0] < SPHERE_WIDTH,
                hood[:,1] < SPHERE_WIDTH,
                hood[:,2] < SPHERE_WIDTH))
    return hood[condition]

# @profile
def get_entropy(probmap, decided):

    decided_deep = decided.reshape(decided.shape[0], decided.shape[1], -1, 1)
    # entropy = np.exp(-np.sum((probmap * np.exp(probmap)) * (probmap > 0).astype(np.int32) * (decided_deep == 0)\
    #         .reshape(decided.shape[0],decided.shape[1],decided.shape[2],1), axis = -1))
    entropy = np.sum((probmap > 0).astype(np.int32) * (decided_deep == 0)\
            .reshape(decided.shape[0],decided.shape[1],decided.shape[2],1), axis = -1)

    entropy += (decided == 1) * 200000#np.max(entropy)
    return entropy

# @profile
def update_entropy_around(i, j, l):
    global probmap
    global entropy
    entropy[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
            max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
            max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)]\
                = get_entropy(probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
                                      max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
                                      max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)],
                              decided[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
                                      max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
                                      max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)])

def normalize_probmap_around(i, j, l):
    global probmap
    p = probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
                max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
                max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)]
    s = np.sum(p, axis = -1)
    p[s==0,:]=1
    s = np.sum(p, axis = -1)

    p /= s.reshape(s.shape[0], s.shape[1], -1, 1)
    probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
            max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
            max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)] = p


def is_valid_around(i, j, l):
    global probmap
    p = probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
                max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
                max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)]
    s = np.sum(p, axis = -1)
    return len(np.where(s==0)[0]) == 0

# @profile
def place(i, j, l, tile_index):
    
    global probmap, fixup_budget
    # print probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
    #               max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
    #               max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)].shape

    # print spheres[tile_index,
    #                max(0, -(i-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, i + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
    #                max(0, -(j-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, j + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
    #                max(0, -(l-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, l + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH)].shape
    # print spheres.shape
    sphere = spheres[tile_index]#.transpose(2,1,0,3)

    old_p = probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
            max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
            max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)].copy()

    probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
            max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
            max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)]\
        *= sphere[
                   max(0, -(i-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, i + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
                   max(0, -(j-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, j + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
                   max(0, -(l-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, l + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH)]

    # probmap = normalize_probmap(probmap)
    
    if not is_valid_around(i, j, l):
        probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
            max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
            max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)] = old_p
        if fixup_budget > 0:
            fixup_budget -= 1
            print "fixing up",i,j,l
            return 
    normalize_probmap_around(i, j, l)
    update_entropy_around(i, j, l)

    decided[i,j,l] = 1
    world[i,j, l] = tile_index
    for i1, j1, l1 in neighbors(i,j,l):
        if in_world(i1, j1, l1):
            surrounded = True
            for i2, j2, l2 in neighbors(i1,j1, l1):
                if in_world(i2, j2, l2):
                    if decided[i2, j2, l2] == 0:
                        surrounded = False
                        break
            if surrounded:
                forget(i1, j1, l1)

def forget(i, j, l):
    global probmap
    s = spheres[world[i,j, l],
                   max(0, -(i-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, i + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
                   max(0, -(j-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, j + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
                   max(0, -(l-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, l + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH)]
    probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
            max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
            max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)]\
        /= s + np.ones_like(s) * (s==0)
    normalize_probmap_around(i,j,l)
    update_entropy_around(i, j,l)


# def unplace(i, j, l):
#     decided[i,j,l] = 0
#     global probmap
#     # print world[i,j], i, j
#     s = spheres[world[i,j,l],
#                    max(0, -(i-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, i + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
#                    max(0, -(j-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, j + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH),
#                    max(0, -(l-SPHERE_WIDTH / 2)) : SPHERE_WIDTH - max(0, l + SPHERE_WIDTH / 2 + 1 - WORLD_WIDTH)]
#     probmap[max(0, i - SPHERE_WIDTH / 2): min(WORLD_WIDTH, i + SPHERE_WIDTH / 2 + 1),
#             max(0, j - SPHERE_WIDTH / 2): min(WORLD_WIDTH, j + SPHERE_WIDTH / 2 + 1),
#             max(0, l - SPHERE_WIDTH / 2): min(WORLD_WIDTH, l + SPHERE_WIDTH / 2 + 1)]\
#         /= s + np.ones_like(s) * (s==0)
#     probmap = normalize_probmap(probmap)
#     update_entropy_around(i, j, l)
#     world[i,j] = 0




def get_all_valid(i,j,l):
    result = []
    for t in range(len(tiles)):
        ismatch = True
        for ni, nj in neighbors(i,j):
            if decided[ni, nj] == 1:
                ismatch = ismatch and match(tiles[t], tiles[world[ni,nj]], ni - i, nj - j)
        if ismatch:
            result.append(t)
    return result


def is_valid(i,j,l):
    for ni, nj, nl in neighbors(i,j,l):
        if decided[ni, nj, nl] == 1:
            ismatch = match(tiles[world[i,j,l]], tiles[world[ni,nj,nl]], ni - i, nj - j, nl - l)
            if not ismatch:
                return False
    return True


def logp(world):
    logp = 0
    for i in range(world.shape[0]):
        for j in range(world.shape[1]):
            logp += np.log(p(i,j,tiles[world[i,j]]))
    print logp


def normalize_probmap(probmap):
    s = np.sum(probmap, axis = -1)
    # s[s==0]=1
    probmap[s==0,:]=1
    s = np.sum(probmap, axis = -1)

    probmap /= s.reshape(WORLD_WIDTH, WORLD_WIDTH, WORLD_WIDTH, 1)
    return probmap


# print "===="
tiles, tile_properties, tile_priors = get_tiles()
print tile_priors


tile_index_to_prior = np.ones(len(tiles)) / len(tiles)
build_transition_matrices(tiles)
import time
t1 = time.time()

spheres = create_spheres(tiles)
print time.time() - t1, "to build tiles"
# print tiles
# print
# for tile in tiles:
#     print tile


def get_air_index():
    for i, props in enumerate(tile_properties):
        if props.name[:3] =="air":
            return i
    assert False, "you must have a tile namex air*.vox"



world = np.zeros((WORLD_WIDTH,WORLD_WIDTH, WORLD_WIDTH)).astype(np.int32)
probmap = np.ones((WORLD_WIDTH,WORLD_WIDTH, WORLD_WIDTH, len(tiles))).astype(np.float32)
probmap *= np.array(tile_priors).reshape([1,1,1,-1])



probmap = normalize_probmap(probmap)
decided = np.zeros((WORLD_WIDTH,WORLD_WIDTH, WORLD_WIDTH)).astype(np.int32)
entropy = np.ones((WORLD_WIDTH,WORLD_WIDTH, WORLD_WIDTH)) * 1000000


all_coords = []

for i in range(world.shape[0]):
    for j in range(world.shape[1]):
        all_coords.append((i,j))

def report_on_probmap_location(i,j):
    print "=================================="
    print "reporting information about probmap at", i, j
    for tile, p in zip(tiles, probmap[i,j]):
        print tile
        print p
        print
    print "=================================="



# @profile
def place_a_tile():
    entropy_argmin = np.unravel_index(np.argmin(entropy  + np.random.normal(size=entropy.shape, scale = .00001)), entropy.shape)
    i,j,l= entropy_argmin
    # print i

    ts, ps = range(len(tiles)), probmap[i,j,l]
    # print "ps", ps
    to_place = np.random.choice(ts, 1, p=np.array(ps))[0]
    # print "placing", to_place, "at", i,j,l
    # l = random.randint(0, WORLD_WIDTH - 1)
    place(i,j,l, to_place)

# @profile
def generate_world():

    # place(2,2, 1)
    # for _ in range(10):
    #    i = random.randint(0, (WORLD_WIDTH - 1) / 10)
    #    j = random.randint(0, (WORLD_WIDTH - 1) / 10)
    #    l = random.randint(0, (WORLD_WIDTH - 1) / 10)
    #    tile = random.choice(range(len(tiles)))
    #    place(i * 10, j * 10, l * 10, tile)

    # draw_world(world, tiles, mask = decided)

    # report_on_sphere(2, spheres, tiles)
    # print probmap[WORLD_WIDTH / 2,WORLD_WIDTH / 2 - 1]
    # report_on_probmap_location(WORLD_WIDTH / 2,WORLD_WIDTH / 2 - 1)
    # quit()

    def state_report():
        print "entropy", entropy.shape
        print entropy[:,:,0]
        print entropy[:,:,1]
        print entropy[:,:,2]
        print "probs", probmap.shape
        print probmap[:,:,:,0]
        print
        print probmap[:,:,:,1]
        print "decided", decided.shape
        print decided[:,:,0]
        print decided[:,:,1]
        print decided[:,:,2]
        print "world", world.shape
        for slicenum in range(world.shape[-1]):
            print world[:,:,slicenum]
    print "=======START GENERATION=========="
    # state_report()
    if SURROUND_BY_AIR:
        air_index = get_air_index()
        for i in range(WORLD_WIDTH):
            for j in range(WORLD_WIDTH):
                for l in range(WORLD_WIDTH):
                    if (i == 0 or i == WORLD_WIDTH-1
                        or j == 0 or j == WORLD_WIDTH-1
                        or l == 0 or l == WORLD_WIDTH-1):
                            if random.random() < 1:
                                place(i, j, l, air_index)


    # place(1,1,1,0)
    # print "placing first tile"
    # state_report()
    # quit()

    # print "placing some tiles..."
    # place_a_tile()
    # state_report()
    # print "placing some tiles..."
    # place_a_tile()
    # state_report()
    # print "placing some tiles..."
    # for _ in range(3):
    #     place_a_tile()
    # state_report()
    
    # return
    step=0
    while np.prod(decided.shape) - np.sum(decided) > 0:
        step += 1
        if step % 1000 == 0:
            print str(100*(step)/np.prod(decided.shape)) + "% done"
        place_a_tile()
        # print "entropy"
        # print entropy
        # print "probs"
        # print probmap[:,:,:,0]
        # print probmap[:,:,:,1]

        # if step % (np.prod(world.shape) / 4) ==0:
            # draw_world(world, tiles, mask = decided)
            # time.sleep(.3)
    # state_report()
    print "generation complete."
generate_world()

print world





worldchars = np.zeros([WORLD_WIDTH*TILE_WIDTH]*3).astype(np.int32)
stride = TILE_WIDTH-1
for i in range(0, WORLD_WIDTH):
    for j in range(0, WORLD_WIDTH):
        for l in range(0, WORLD_WIDTH):
            if not tile_properties[world[i,WORLD_WIDTH-j-1,l]].is_air:
                worldchars[i*stride:i*stride+TILE_WIDTH,j*stride:j*stride+TILE_WIDTH,l*stride:l*stride+TILE_WIDTH] \
                     = tiles[world[i,WORLD_WIDTH-j-1,l]][:,::-1,:]
            else:
                worldchars[i*stride:i*stride+TILE_WIDTH,j*stride:j*stride+TILE_WIDTH,l*stride:l*stride+TILE_WIDTH] = 0


print "writing .vox output"

a = (worldchars).astype(np.int32)
print a
vox = Vox.from_dense(a)
VoxWriter('test.vox', vox).write()


