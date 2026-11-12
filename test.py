import pickle
import numpy as np
import time
from agv_env import FullAGVFactoryEnv, discretize_observation
from viewer import AGVViewer

STEP_DELAY = 0.12


# Q-tablosuna göre mevcut durum için en yüksek değerli eylemi seçer, durum tabloda yoksa rastgele eylem döndürür.
def select_greedy_action(q_tables: dict, agent: str, state: tuple, action_space) -> int:
    if state in q_tables[agent]:
        return int(np.argmax(q_tables[agent][state]))
    return action_space.sample()


# Eğitilmiş Q-tablosunu yükleyerek ajanların performansını görsel simülasyon üzerinde test eder.
def test(episodes=5):
    try:
        with open("q_table.pkl", "rb") as f:
            q_tables = pickle.load(f)
    except FileNotFoundError:
        print("Hata: 'q_table.pkl' bulunamadı! Önce 'python train.py' ile eğitim yapmalısınız.")
        return

    env = FullAGVFactoryEnv()
    viewer = AGVViewer(env)

    for ep in range(1, episodes + 1):
        obs, _ = env.reset()
        print(f"\n--- Bölüm {ep} Başlatılıyor ---")

        while env.agents:
            viewer.render()
            time.sleep(STEP_DELAY)

            actions = {
                a: select_greedy_action(q_tables, a, discretize_observation(obs[a]), env.action_spaces[a])
                for a in env.agents
            }
            obs, rewards, terminations, truncations, _ = env.step(actions)

        print(f"Adım: {env.num_moves} | Teslimat: {env.deliveries} | Çarpışma girişimi: {env.collisions} | "
              f"Batarya: {env.batteries}")


if __name__ == "__main__":
    test()
