import pickle
import random
import time
import numpy as np
import matplotlib.pyplot as plt
from agv_env import FullAGVFactoryEnv, discretize_observation

ALPHA = 0.1
GAMMA = 0.97
EPSILON_START = 1.0
EPSILON_MIN = 0.02
TOTAL_EPISODES = 60000
EXPLORE_FRACTION = 0.8
SOLO_FRACTION = 0.15
RANDOM_START_PROB = 0.5


# Belirtilen ajan ve durum için Q değerlerini döndürür, durum tabloda yoksa sıfırlardan oluşan dizi başlatır.
def get_q(q_tables: dict, agent: str, state: tuple, n_actions: int) -> np.ndarray:
    if state not in q_tables[agent]:
        q_tables[agent][state] = np.zeros(n_actions)
    return q_tables[agent][state]


# Epsilon-greedy stratejisine göre rastgele veya en yüksek Q değerine sahip eylemi seçer.
def select_action(q_vals: np.ndarray, epsilon: float, n_actions: int) -> int:
    if random.random() < epsilon:
        return random.randrange(n_actions)
    max_indices = np.flatnonzero(q_vals == q_vals.max())
    return int(random.choice(max_indices))


# Eğitim sürecinde toplanan metrikleri ve hareketli ortalamalarını grafik olarak dosyaya kaydeder.
def save_plot(values: list, window: int, title: str, ylabel: str, filename: str):
    plt.figure(figsize=(10, 5))
    plt.plot(values, label="Bölüm Değeri", color="lightblue", alpha=0.4)
    if len(values) >= window:
        moving_avg = np.convolve(values, np.ones(window) / window, mode="valid")
        plt.plot(range(window - 1, len(values)), moving_avg, label=f"Son {window} Bölüm Ortalaması", color="red", linewidth=2)
    plt.title(title)
    plt.xlabel("Bölüm (Episode)")
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


# Ajanları Q-Learning algoritmasıyla eğitir, Q-tablosunu ve eğitim grafiklerini kaydeder.
def train():
    env = FullAGVFactoryEnv(gamma=GAMMA)
    q_tables = {a: {} for a in env.possible_agents}
    rewards_history = {a: [] for a in env.possible_agents}
    steps_history, deliveries_history, collisions_history = [], [], []

    solo_eps = int(TOTAL_EPISODES * SOLO_FRACTION)
    explore_eps = int(TOTAL_EPISODES * EXPLORE_FRACTION)
    print(f"Çift Döngülü AGV Eğitimi Başlıyor | Toplam Bölüm: {TOTAL_EPISODES}")
    t0 = time.time()

    for ep in range(1, TOTAL_EPISODES + 1):
        # Epsilon değerini güncelle ve bölüm başlangıç ayarlarını belirle
        epsilon = max(EPSILON_MIN, EPSILON_START - (EPSILON_START - EPSILON_MIN) * ep / explore_eps)
        options = {"random_start": random.random() < RANDOM_START_PROB}
        if ep <= solo_eps:
            options["agents"] = [random.choice(env.possible_agents)]

        obs, _ = env.reset(options=options)
        states = {a: discretize_observation(obs[a]) for a in env.agents}

        # Bölüm bitene kadar ajanların eylemlerini uygula ve Q-tablolarını güncelle
        while env.agents:
            actions = {
                a: select_action(get_q(q_tables, a, states[a], 5), epsilon, 5)
                for a in env.agents
            }
            next_obs, rewards, terminations, truncations, infos = env.step(actions)

            for a, action in actions.items():
                q_vals = get_q(q_tables, a, states[a], 5)
                r = rewards[a] + infos[a]["shaping"]

                if terminations[a]:
                    target = r
                else:
                    next_state = discretize_observation(next_obs[a]) if a in next_obs else None
                    if next_state is None:
                        next_state = states[a]
                    target = r + GAMMA * np.max(get_q(q_tables, a, next_state, 5))
                    states[a] = next_state

                q_vals[action] += ALPHA * (target - q_vals[action])

        # Çok ajanlı eğitim aşamasındaki bölüm istatistiklerini kaydet
        if ep > solo_eps:
            for a in env.possible_agents:
                rewards_history[a].append(env.total_rewards[a])
            steps_history.append(env.num_moves)
            deliveries_history.append(sum(env.deliveries.values()))
            collisions_history.append(env.collisions)

        if ep % 5000 == 0:
            n = 500
            d = np.mean(deliveries_history[-n:]) if deliveries_history else 0
            s = np.mean(steps_history[-n:]) if steps_history else 0
            c = np.mean(collisions_history[-n:]) if collisions_history else 0
            print(f"Bölüm: {ep:5d}/{TOTAL_EPISODES} | Eps: {epsilon:.3f} | Adım: {s:6.1f} | "
                  f"Teslimat (maks 4): {d:.2f} | Çarpışma: {c:.2f} | "
                  f"State: {len(q_tables['agv_0'])}/{len(q_tables['agv_1'])} | {time.time() - t0:.0f}s")

    # Eğitilen Q-tablosunu ve performans grafiklerini kaydet
    with open("q_table.pkl", "wb") as f:
        pickle.dump(q_tables, f)
    print("Ağırlıklar kaydedildi: 'q_table.pkl'")

    save_plot(rewards_history["agv_0"], 250, "AGV 0 - Eğitim Süreci", "Ödül (Reward)", "agv0_egitim_grafigi.png")
    save_plot(rewards_history["agv_1"], 250, "AGV 1 - Eğitim Süreci", "Ödül (Reward)", "agv1_egitim_grafigi.png")
    save_plot(steps_history, 250, "Bölüm Başına Adım Sayısı", "Adım Sayısı (Steps)", "adim_sayisi_grafigi.png")
    save_plot(deliveries_history, 250, "Bölüm Başına Toplam Teslimat (maks 4)", "Teslimat", "teslimat_grafigi.png")
    save_plot(collisions_history, 250, "Bölüm Başına Çarpışma Girişimi", "Çarpışma", "carpisma_grafigi.png")
    print("Grafikler oluşturuldu.")


if __name__ == "__main__":
    train()
