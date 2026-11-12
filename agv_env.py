import numpy as np
import random
from collections import deque
from pettingzoo import ParallelEnv
from gymnasium.spaces import Discrete, Box

MOVES = {0: (0, 0), 1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}

R_STEP = -1.0
R_WALL = -1.0
R_PICKUP = 10.0
R_DELIVERY = 100.0
R_TEAM_DELIVERY = 30.0
R_MISSION_DONE = 50.0
R_COLLISION = -40.0
R_BATTERY_DEAD = -100.0

LOW_BATTERY = 25
CHARGE_RATE = 20
MOVE_DRAIN = 1.0
LOAD_EXTRA_DRAIN = 1.0
IDLE_DRAIN = 0.5

SHAPING_K = 1.0
STAGE_VALUE = 25.0
LOW_BAT_PENALTY = 30.0

MAX_STEPS = 300
REL_WINDOW = 2


# Sürekli gözlem vektörünü Q-tablosunda kullanılmak üzere ayrık bir duruma dönüştürür.
def discretize_observation(obs: np.ndarray) -> tuple:
    (x, y, bat, payload, deliveries, rdx, rdy,
     other_present, other_payload, other_in_corr, w_stock, e_stock) = obs
    bat_level = 2 if bat > 50 else (1 if bat > LOW_BATTERY else 0)

    if other_present and abs(rdx) <= REL_WINDOW and abs(rdy) <= REL_WINDOW:
        rel = (int(rdx), int(rdy))
    else:
        rel = (9, 9)

    corr = int(1 + other_payload) if (other_present and other_in_corr) else 0
    relevant_stock = int(w_stock) if x <= 5 else int(e_stock)

    return (int(x), int(y), int(payload), int(deliveries), bat_level, rel, corr, relevant_stock)


class FullAGVFactoryEnv(ParallelEnv):
    metadata = {"name": "agv_factory_v5"}

    # Fabrika ortamının boyutlarını, istasyon noktalarını, duvarları ve mesafe haritalarını başlatır.
    def __init__(self, gamma: float = 0.97):
        super().__init__()
        self.possible_agents = ["agv_0", "agv_1"]
        self.width = 12
        self.height = 8
        self.gamma = gamma

        self.action_spaces = {a: Discrete(5) for a in self.possible_agents}
        self.observation_spaces = {
            a: Box(low=-20, high=100, shape=(12,), dtype=np.float32)
            for a in self.possible_agents
        }

        self.walls = {(x, y) for x in range(3, 9) for y in range(8) if y != 4}
        self.corridor = {(x, 4) for x in range(3, 9)}
        self.charging_stations = {(0, 0), (11, 0), (0, 7), (11, 7)}

        self.WEST_PICKUP = np.array([1, 2])
        self.EAST_DROPOFF = np.array([10, 6])
        self.EAST_PICKUP = np.array([10, 2])
        self.WEST_DROPOFF = np.array([1, 6])

        self.free_cells = [(x, y) for x in range(self.width) for y in range(self.height)
                           if (x, y) not in self.walls]

        # Ödül şekillendirmede kullanmak için hedeflere olan en kısa mesafeleri hesaplar
        self._dist = {}
        for name, cells in {
            "west_pickup": [tuple(self.WEST_PICKUP)],
            "east_pickup": [tuple(self.EAST_PICKUP)],
            "west_dropoff": [tuple(self.WEST_DROPOFF)],
            "east_dropoff": [tuple(self.EAST_DROPOFF)],
            "charger": list(self.charging_stations),
        }.items():
            self._dist[name] = self._bfs(cells)

    # Verilen hedef hücrelerden haritadaki tüm geçilebilir hücrelere olan en kısa mesafeyi BFS ile hesaplar.
    def _bfs(self, sources):
        dist = {c: 0 for c in sources}
        q = deque(sources)
        while q:
            x, y = q.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                n = (x + dx, y + dy)
                if (0 <= n[0] < self.width and 0 <= n[1] < self.height
                        and n not in self.walls and n not in dist):
                    dist[n] = dist[(x, y)] + 1
                    q.append(n)
        return dist

    # Verilen ajanın dışındaki diğer ajanın adını döndürür.
    def _get_other_agent(self, agent: str) -> str:
        return "agv_1" if agent == "agv_0" else "agv_0"

    # Ajanın mevcut yük durumuna ve konumuna göre gitmesi gereken hedef istasyonu belirler.
    def _task_target(self, agent: str) -> str:
        p = self.payload[agent]
        if p == 1:
            return "east_dropoff"
        if p == 2:
            return "west_dropoff"
        return "west_pickup" if self.positions[agent][0] <= 5 else "east_pickup"

    # Ödül şekillendirme için ajanın görev ilerlemesine ve hedefe uzaklığına göre potansiyel değerini hesaplar.
    def potential(self, agent: str) -> float:
        stage = 2 * self.deliveries[agent] + (1 if self.payload[agent] != 0 else 0)
        pos = tuple(self.positions[agent])
        if self.batteries[agent] <= LOW_BATTERY:
            d = self._dist["charger"][pos]
            return SHAPING_K * (STAGE_VALUE * stage - d) - LOW_BAT_PENALTY
        d = self._dist[self._task_target(agent)][pos]
        return SHAPING_K * (STAGE_VALUE * stage - d)

    # Ortamı başlangıç durumuna sıfırlar ve ilk gözlemleri döndürür.
    def reset(self, seed=None, options=None):
        options = options or {}
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.agents = list(options.get("agents", self.possible_agents))
        self.positions = {"agv_0": np.array([2, 4]), "agv_1": np.array([9, 4])}
        self.batteries = {"agv_0": 100, "agv_1": 100}

        if options.get("random_start", False):
            west = [c for c in self.free_cells if c[0] <= 2]
            east = [c for c in self.free_cells if c[0] >= 9]
            p0 = random.choice(west)
            p1 = random.choice([c for c in east if c != p0])
            self.positions = {"agv_0": np.array(p0), "agv_1": np.array(p1)}
            self.batteries = {a: random.randint(40, 100) for a in self.possible_agents}

        self.payload = {"agv_0": 0, "agv_1": 0}
        self.station_stock = {"west": True, "east": True}
        self.deliveries = {"agv_0": 0, "agv_1": 0}
        self.total_rewards = {"agv_0": 0.0, "agv_1": 0.0}
        self.collisions = 0
        self.num_moves = 0
        return self._get_obs(), {a: {} for a in self.agents}

    # Verilen konumun dar koridor içerisinde olup olmadığını kontrol eder.
    def _in_corridor(self, pos) -> bool:
        return (int(pos[0]), int(pos[1])) in self.corridor

    # Aktif ajanların konum, batarya, yük ve çevre bilgilerini içeren gözlem vektörlerini oluşturur.
    def _get_obs(self) -> dict:
        obs = {}
        for a in self.agents:
            other = self._get_other_agent(a)
            present = other in self.agents
            if present:
                rdx, rdy = self.positions[other] - self.positions[a]
                o_pay = self.payload[other]
                o_corr = 1.0 if self._in_corridor(self.positions[other]) else 0.0
            else:
                rdx, rdy, o_pay, o_corr = 0, 0, 0, 0.0
            obs[a] = np.array([
                self.positions[a][0], self.positions[a][1],
                self.batteries[a],
                float(self.payload[a]),
                float(min(self.deliveries[a], 1)),
                float(rdx), float(rdy),
                1.0 if present else 0.0,
                float(o_pay), o_corr,
                1.0 if self.station_stock["west"] else 0.0,
                1.0 if self.station_stock["east"] else 0.0,
            ], dtype=np.float32)
        return obs

    # Hedef hücrenin harita sınırları içinde ve duvar olmayan geçerli bir alan olup olmadığını kontrol eder.
    def _valid(self, pos) -> bool:
        x, y = int(pos[0]), int(pos[1])
        return 0 <= x < self.width and 0 <= y < self.height and (x, y) not in self.walls

    # Ajanların seçtiği eylemleri uygular, çarpışma, batarya ve görev durumlarını güncelleyip yeni durumu döndürür.
    def step(self, actions: dict):
        old_pos = {a: self.positions[a].copy() for a in self.agents}
        phi_old = {a: self.potential(a) for a in self.agents}
        rewards = {a: R_STEP for a in self.agents}

        # Yeni konumları hesapla ve duvar çarpışmalarını kontrol et
        proposed = {}
        for a, act in actions.items():
            np_ = old_pos[a] + np.array(MOVES[act])
            if self._valid(np_):
                proposed[a] = np_
            else:
                proposed[a] = old_pos[a].copy()
                rewards[a] += R_WALL

        # İki ajan aynı hücreye girmeye veya yer değiştirmeye çalışırsa çarpışma cezası uygula
        if len(self.agents) == 2:
            a0, a1 = self.agents
            same = np.array_equal(proposed[a0], proposed[a1])
            swap = (np.array_equal(proposed[a0], old_pos[a1]) and
                    np.array_equal(proposed[a1], old_pos[a0]))
            if same or swap:
                moved0 = not np.array_equal(proposed[a0], old_pos[a0])
                moved1 = not np.array_equal(proposed[a1], old_pos[a1])
                for a, moved in ((a0, moved0), (a1, moved1)):
                    if moved:
                        rewards[a] += R_COLLISION
                        proposed[a] = old_pos[a].copy()
                self.collisions += 1

        # Hareketleri uygula ve eyleme göre batarya seviyesini güncelle
        for a, act in actions.items():
            self.positions[a] = proposed[a]
            pos = tuple(self.positions[a])
            if act == 0 and pos in self.charging_stations:
                self.batteries[a] = min(100.0, self.batteries[a] + CHARGE_RATE)
            elif act == 0:
                self.batteries[a] -= IDLE_DRAIN
            else:
                self.batteries[a] -= MOVE_DRAIN + (LOAD_EXTRA_DRAIN if self.payload[a] != 0 else 0.0)

        # Boşalan istasyonlara belirli bir olasılıkla yeni stok ekle
        if not self.station_stock["west"] and random.random() < 0.14:
            self.station_stock["west"] = True
        if not self.station_stock["east"] and random.random() < 0.14:
            self.station_stock["east"] = True

        # Yük alma, teslimat yapma ve batarya bitmesi durumlarını kontrol et
        terminations = {a: False for a in self.agents}
        for a in actions:
            pos = self.positions[a]
            other = self._get_other_agent(a)
            if self.payload[a] == 0:
                if np.array_equal(pos, self.WEST_PICKUP) and self.station_stock["west"]:
                    self.payload[a] = 1
                    self.station_stock["west"] = False
                    rewards[a] += R_PICKUP
                elif np.array_equal(pos, self.EAST_PICKUP) and self.station_stock["east"]:
                    self.payload[a] = 2
                    self.station_stock["east"] = False
                    rewards[a] += R_PICKUP
            elif ((self.payload[a] == 1 and np.array_equal(pos, self.EAST_DROPOFF)) or
                  (self.payload[a] == 2 and np.array_equal(pos, self.WEST_DROPOFF))):
                self.payload[a] = 0
                self.deliveries[a] += 1
                rewards[a] += R_DELIVERY
                if other in rewards:
                    rewards[other] += R_TEAM_DELIVERY
                if self.deliveries[a] >= 2:
                    rewards[a] += R_MISSION_DONE
                    terminations[a] = True

            if self.batteries[a] <= 0 and not terminations[a]:
                rewards[a] += R_BATTERY_DEAD
                terminations[a] = True

        # Potansiyel tabanlı ödül şekillendirme değerlerini hesapla ve adım bilgilerini güncelle
        self.shaping = {}
        for a in actions:
            f = self.gamma * self.potential(a) - phi_old[a]
            self.shaping[a] = f

        self.num_moves += 1
        is_timeout = self.num_moves >= MAX_STEPS
        truncations = {a: (is_timeout and not terminations[a]) for a in self.agents}
        infos = {a: {"shaping": self.shaping[a]} for a in self.agents}

        for a in actions:
            self.total_rewards[a] += rewards[a]

        self.agents = [a for a in self.agents if not (terminations[a] or truncations[a])]
        return self._get_obs(), rewards, terminations, truncations, infos
