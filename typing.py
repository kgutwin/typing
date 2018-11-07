#!/usr/bin/env python

import time
import curses
import random
from collections import namedtuple


TICK = 0.1
CityColumn = namedtuple('CityColumn', ['chr', 'height'])

class Invader:
    def __init__(self, c, init_x):
        self.c = c
        self.x = init_x
        self.y = 0
        self.damage = 0
        self.fall_ticks_left = 0
        self.exploded = False

    @classmethod
    def new(cls, c, max_x):
        x = 9e99
        while x + len(c) > max_x:
            x = random.randint(0, max_x)
        return cls(c, x)

    def draw_to(self, scr):
        if len(self) <= self.damage <= len(self) + 3:
            # animate an explosion
            self.damage += 1
            frame = self.damage - (1 + len(self))
            x = '@' if self.exploded else '*'
            if frame == 0:
                scr.addstr(self.y, self.x, x * len(self))
            elif frame == 1:
                if len(self) == 1:
                    scr.addstr(self.y, self.x - 1, x * 3)
                else:
                    scr.addstr(self.y, self.x - 1,
                               x * 2 + (' ' * (len(self) - 2)) + x * 2)
            elif frame >= 2:
                scr.addstr(self.y - 1, self.x - 2,
                           x + (' ' * (len(self) + 2)) + x)
                scr.addstr(self.y, self.x - 1, x + (' ' * len(self)) + x)
                scr.addstr(self.y + 1, self.x - 2,
                           x + (' ' * (len(self) + 2)) + x)

        elif self.damage > 0:
            typed = self.c[:self.damage]
            scr.addstr(self.y, self.x, typed, curses.A_BOLD)
            scr.addstr(self.y, self.x+len(typed), self.c[self.damage:])
        else:
            scr.addstr(self.y, self.x, self.c)

    def fall(self, speed):
        if self.destroyed or self.exploded:
            return
        
        if self.fall_ticks_left == 0:
            self.y += 1
            self.fall_ticks_left = speed
        else:
            self.fall_ticks_left -= 1

    def hit_by(self, c):
        if c is None or self.disabled or self.exploded:
            return False
        
        if c == self.c[self.damage]:
            self.damage += 1
            return True
        
        return False

    def explode(self):
        if not self.exploded:
            self.exploded = True
            self.damage = len(self)
    
    def __len__(self):
        return len(self.c)

    @property
    def disabled(self):
        if self.exploded:
            return False
        return self.damage >= len(self)

    @property
    def destroyed(self):
        return self.damage >= len(self) + 3


class Level:
    def __init__(self, n, word_list, previous_points=0):
        self.n = n
        self.word_list = word_list
        self.points = previous_points
        self.invaders = []
        self.invaders_left = 100
        self.speed = 10 # number of TICKs per fall
        self.create_new_in = 10
        self.max_x = 10
        self.city = []
        self.city_bottom = 99

    def hit_city(self, i):
        if i.exploded or i.disabled:
            return False
        
        h = self.city_bottom - i.y
        hit = False
        for col in [i.x + n for n in range(len(i))]:
            if max(self.city[col].height, 1) >= h:
                hit = True
                
        if hit:
            hit_start = max(0, i.x - 1)
            hit_end = min(len(self.city), i.x + len(i) + 1)
            for col in range(hit_start, hit_end):
                if self.city[col].height >= (h - 2):
                    new_height = max(0, h - 2)
                    self.city[col] = CityColumn(self.city[col].chr,
                                                new_height)

        return hit
        
    def move(self, c=None):
        any_destroyed = False
        for i in self.invaders:
            if i.hit_by(c):
                c = None
            if i.disabled:
                self.points += self.n * len(i)
            else:
                i.fall(self.speed)

            if i.destroyed:
                any_destroyed = True
                if not i.exploded:
                    self.invaders_left -= 1
                    if self.invaders_left % 12 == 0:
                        self.speed -= 1

            if self.hit_city(i):
                i.explode()
                #self.points -= self.n * len(i) * 4

        if any_destroyed:
            self.invaders = [i for i in self.invaders if not i.destroyed]

        if self.create_new_in > 0:
            self.create_new_in -= 1
        elif self.invaders_left > 0:
            word = random.choice(self.word_list)
            self.invaders.append(Invader.new(word, self.max_x))
            self.create_new_in = random.randint(10, 20)
        
    def draw(self, scr):
        height, width = scr.getmaxyx()
        self.max_x = width - 1
        self.city_bottom = height - 2
        while len(self.city) < self.max_x:
            block_char = random.choice('#=|.')
            block_width = min(random.randint(1, 5), self.max_x - len(self.city))
            block_height = max(block_width - 1, random.randint(1, 5))
            for i in range(block_width):
                self.city.append(CityColumn(block_char, block_height))

        for i, c in enumerate(self.city):
            if c.height:
                scr.vline(height - (2 + c.height), i, c.chr, c.height)
                
        if self.complete:
            scr.addstr(height / 2, (width / 2) - 5,
                       'GOOD JOB!')

        elif self.game_over:
            scr.addstr(height / 2, (width / 2) - 7,
                       'G A M E   O V E R')
            
        else:
            for i in self.invaders:
                try:
                    i.draw_to(scr)
                except curses.error:
                    pass

        scr.hline(height - 2, 0, '-', width)
        scr.addstr(height - 1, 0,
                   'Level %2d     Score: %6d   Remaining: %3d' % (
                       self.n, self.points, self.invaders_left))

    @property
    def complete(self):
        return self.invaders_left == 0

    @property
    def game_over(self):
        return self.city and all(c.height == 0 for c in self.city)


GAME_WORDS = [
    "a", "about", "above", "above", "across", "after", "afterwards", "again",
    "against", "all", "almost", "alone", "along", "already", "also",
    "although","always","am", "among", "amongst", "amount",  "an",
    "and", "another", "any", "anyhow", "anyone", "anything", "anyway",
    "anywhere",
    "are", "around", "as",  "at", "back", "be", "became", "because", "become",
    "becomes", "becoming", "been", "before", "beforehand", "behind", "being",
    "below", "beside", "besides", "between", "beyond", "bill", "both",
    "bottom", "but", "by", "call", "can", "cannot", "cant", "co", "con",
    "could", "couldnt", "cry", "de", "describe", "detail", "do", "done",
    "down", "due", "during", "each", "eg", "eight", "either", "eleven",
    "else", "elsewhere", "empty", "enough", "etc", "even", "ever", "every",
    "everyone", "everything", "everywhere", "except", "few", "fifteen",
    "fifty", "fill", "find", "fire", "first", "five", "for", "former",
    "formerly", "forty", "found", "four", "from", "front", "full", "further",
    "get", "give", "go", "had", "has", "hasnt", "have", "he", "hence", "her",
    "here", "hereafter", "hereby", "herein", "hereupon", "hers", "herself",
    "him", "himself", "his", "how", "however", "hundred", "ie", "if", "in",
    "inc", "indeed", "interest", "into", "is", "it", "its", "itself", "keep",
    "last", "latter", "latterly", "least", "less", "ltd", "made", "many",
    "may", "me", "meanwhile", "might", "mill", "mine", "more", "moreover",
    "most", "mostly", "move", "much", "must", "my", "myself", "name",
    "namely", "neither", "never", "nevertheless", "next", "nine", "no",
    "nobody", "none", "noone", "nor", "not", "nothing", "now", "nowhere",
    "of", "off", "often", "on", "once", "one", "only", "onto", "or", "other",
    "others", "otherwise", "our", "ours", "ourselves", "out", "over", "own",
    "part", "per", "perhaps", "please", "put", "rather", "re", "same", "see",
    "seem", "seemed", "seeming", "seems", "serious", "several", "she",
    "should", "show", "side", "since", "sincere", "six", "sixty", "so",
    "some", "somehow", "someone", "something", "sometime", "sometimes",
    "somewhere", "still", "such", "system", "take", "ten", "than", "that",
    "the", "their", "them", "themselves", "then", "thence", "there",
    "thereafter", "thereby", "therefore", "therein", "thereupon", "these",
    "they", "thick", "thin", "third", "this", "those", "though", "three",
    "through", "throughout", "thru", "thus", "to", "together", "too", "top",
    "toward", "towards", "twelve", "twenty", "two", "un", "under", "until",
    "up", "upon", "us", "very", "via", "was", "we", "well", "were", "what",
    "whatever", "when", "whence", "whenever", "where", "whereafter",
    "whereas", "whereby", "wherein", "whereupon", "wherever", "whether",
    "which", "while", "whither", "who", "whoever", "whole", "whom", "whose",
    "why", "will", "with", "within", "without", "would", "yet", "you",
    "your", "yours", "yourself", "yourselves", "the"]

GAME_LEVELS = [
    'asdfjkl',
    'asdfjklrtgvbyuhnm',
    'jklyuiophnm',
    'qwertasdfgzxcvb',
    'qwertyuiopasdfghjklzxcvbnm',
    list('abcdefghijklmnopqrstuvwxyz') + [w for w in GAME_WORDS if len(w) == 2],
    list('abcdefghijklmnopqrstuvwxyz') + [w for w in GAME_WORDS if len(w) <= 3],
    list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + [w for w in GAME_WORDS if len(w) <= 3],
    [w for w in GAME_WORDS if len(w) in (3, 4)],
    [w for w in GAME_WORDS if len(w) in (4, 5)],
]

LEVEL = None

def draw_screen(scr):
    global LEVEL
    scr.erase()
    LEVEL.draw(scr)
    scr.refresh()

    if LEVEL.complete:
        time.sleep(5)
        LEVEL = Level(LEVEL.n + 1,
                      GAME_LEVELS[LEVEL.n],
                      LEVEL.points)


def process_input(scr):
    try:
        c = scr.getkey()
    except curses.error:
        c = ''
    
    if c == 'KEY_END':
        return False

    if c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
        LEVEL.move(c)
    else:
        LEVEL.move()
    
    return True


def main(stdscr):
    global LEVEL
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.leaveok(1)
    
    running = True
    LEVEL = Level(1, GAME_LEVELS[0])
    while running:
        draw_screen(stdscr)
        if LEVEL.game_over:
            time.sleep(5)
            running = False
        else:
            running = process_input(stdscr)
            time.sleep(TICK)


if __name__ == '__main__':
    curses.wrapper(main)

