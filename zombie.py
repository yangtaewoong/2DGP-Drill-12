from pico2d import *

import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import play_mode


# zombie Run Speed
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# zombie Action Speed
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')


    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0      # radian 값으로 방향을 표시
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0

        self.build_behavior_tree()
        self.patrol_locations = [(43, 274), (1118, 274), (1050, 494), (575, 804), (235, 991), (575, 804), (1050, 494),
                                 (1118, 274)]
        self.loc_no = 0

    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50


    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        self.bt.run()


    def draw(self):
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)
        self.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        draw_rectangle(*self.get_bb())

    def handle_event(self, event):
        pass

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1


    def set_target_location(self, x=None, y=None):
        if not x or not y:
            raise ValueError('Location should be given')
            self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS

    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distance2 < (PIXEL_PER_METER * r) ** 2

    def move_slightly_to(self, tx, ty):
        self.dir = math.atan2(ty - self.y, tx - self.x)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

    def move_to(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(self.tx, self.ty)
        if self.distance_less_than(self.tx, self.ty, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def set_random_location(self):
        self.tx, self.ty = random.randint(100, 1280 - 100), random.randint(100, 1024 - 100)
        return BehaviorTree.SUCCESS

    def is_boy_nearby(self, r):
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def move_to_boy(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(play_mode.boy.x, play_mode.boy.y)
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def get_patrol_location(self):
        self.tx, self.ty = self.patrol_locations[self.loc_no]
        self.loc_no = (self.loc_no + 1) % len(self.patrol_locations)
        return BehaviorTree.SUCCESS

    def build_behavior_tree(self):
        a1 = Action('Set target location', self.set_target_location, 1000, 1000)
        a2 = Action('Move to', self.move_to)
        a5 = Action('순찰 위치 가져오기', self.get_patrol_location)
        patrol = Sequence('순찰', a5, a2)

        a3 = Action('Set random location', self.set_random_location)
        wander = Sequence('배회', a3, a2)

        def is_boy_in_range():
            return BehaviorTree.SUCCESS if self.is_boy_nearby(7) else BehaviorTree.FAIL

        c1 = Condition('소년이 7미터 범위 안에 있는가?', is_boy_in_range)

        def compare_ball_count():
            if self.ball_count > play_mode.boy.ball_count:
                return BehaviorTree.SUCCESS
            else:
                return BehaviorTree.FAIL

        ball_count_condition = Condition('공 개수 비교', compare_ball_count)

        a4 = Action('소년한테 접근', self.move_to_boy)
        chase_boy = Sequence('소년 추적', ball_count_condition, a4)

        def flee_from_boy():
            self.state = 'Walk'
            boy_dir = math.atan2(play_mode.boy.y - self.y, play_mode.boy.x - self.x)
            flee_dir = boy_dir + math.pi
            distance = RUN_SPEED_PPS * game_framework.frame_time

            # 도망 위치 계산
            new_x = self.x + distance * math.cos(flee_dir)
            new_y = self.y + distance * math.sin(flee_dir)

            screen_left = 50
            screen_right = 1280 - 50
            screen_bottom = 50
            screen_top = 1024 - 50

            self.x = max(screen_left, min(new_x, screen_right))
            self.y = max(screen_bottom, min(new_y, screen_top))

            if self.distance_less_than(self.x, self.y, play_mode.boy.x, play_mode.boy.y, 10):
                return BehaviorTree.RUNNING
            else:
                return BehaviorTree.SUCCESS

        flee = Action('도망', flee_from_boy)

        def check_after_flee():
            if not self.is_boy_nearby(7):
                self.state = 'Idle'
                return BehaviorTree.SUCCESS
            else:
                return BehaviorTree.FAIL

        check_distance_after_flee = Action('도망 후 거리 확인', check_after_flee)

        flee_and_wander = Sequence('도망 후 배회', flee, check_distance_after_flee, wander)

        chase_or_flee = Selector('추적 또는 도망', chase_boy, flee_and_wander)

        chase_or_flee_when_near = Sequence('소년이 가까우면 행동', c1, chase_or_flee)

        root = Selector('행동 선택', chase_or_flee_when_near, patrol, wander)
        self.bt = BehaviorTree(root)




