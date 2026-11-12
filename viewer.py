import pygame

class AGVViewer:
    COLORS = {
        "bg": (24, 26, 32),
        "grid": (38, 42, 52),
        "wall": (55, 60, 72),
        "charge": (39, 174, 96),
        "load_w2e": (52, 152, 219),
        "load_e2w": (230, 126, 34),
        "text": (240, 240, 240),
        "agv_0": (41, 128, 185),
        "agv_1": (211, 84, 0),
        "stock_ready": (46, 204, 113),
        "stock_empty": (140, 145, 155),
        "station_box": (35, 38, 48)
    }

    # Pygame penceresini, ekran boyutlarını ve yazı tiplerini başlatır.
    def __init__(self, env, cell_size=60):
        pygame.init()
        self.env = env
        self.cs = cell_size
        self.w = env.width * cell_size
        self.h = env.height * cell_size + 70
        self.screen = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption("Çift Döngülü Akıllı AGV Fabrika Simülasyonu")
        self.font = pygame.font.SysFont("Consolas", 12, bold=True)
        self.label_font = pygame.font.SysFont("Segoe UI", 10, bold=True)
        self.sub_font = pygame.font.SysFont("Segoe UI", 9, bold=True)

    # Simülasyon ekranını her adımda yeniden çizer ve pencere olaylarını kontrol eder.
    def render(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        self.screen.fill(self.COLORS["bg"])
        self._draw_grid()
        self._draw_stations()
        self._draw_agents()
        self._draw_dashboard()
        pygame.display.flip()
        pygame.time.delay(40)

    # Harita üzerindeki ızgara çizgilerini ve duvarları çizer.
    def _draw_grid(self):
        cs = self.cs
        for x in range(0, self.w + 1, cs):
            pygame.draw.line(self.screen, self.COLORS["grid"], (x, 0), (x, self.env.height * cs))
        for y in range(0, self.env.height * cs + 1, cs):
            pygame.draw.line(self.screen, self.COLORS["grid"], (0, y), (self.w, y))

        for wx, wy in self.env.walls:
            pygame.draw.rect(self.screen, self.COLORS["wall"], (wx * cs, wy * cs, cs, cs))

    # Şarj, yük alma ve teslimat istasyonlarını güncel stok durumlarıyla birlikte çizer.
    def _draw_stations(self):
        cs = self.cs
        # Şarj istasyonlarını çiz
        for cx, cy in self.env.charging_stations:
            rect = (cx * cs + 4, cy * cs + 4, cs - 8, cs - 8)
            pygame.draw.rect(self.screen, self.COLORS["charge"], rect, border_radius=6)
            text = self.label_font.render("ŞARJ", True, self.COLORS["text"])
            self.screen.blit(text, (cx * cs + 15, cy * cs + 22))

        # Yük alma istasyonlarını stok durumuna göre çiz
        wx, wy = self.env.WEST_PICKUP
        w_ready = self.env.station_stock["west"]
        w_color = self.COLORS["stock_ready"] if w_ready else self.COLORS["stock_empty"]
        pygame.draw.rect(self.screen, self.COLORS["station_box"], (wx * cs + 4, wy * cs + 4, cs - 8, cs - 8), border_radius=4)
        pygame.draw.rect(self.screen, w_color, (wx * cs + 4, wy * cs + 4, cs - 8, cs - 8), 2, border_radius=4)
        self.screen.blit(self.label_font.render("BATI AL", True, w_color), (wx * cs + 8, wy * cs + 12))
        self.screen.blit(self.sub_font.render("DOLU" if w_ready else "BEKLE", True, w_color), (wx * cs + 14, wy * cs + 34))

        ex, ey = self.env.EAST_PICKUP
        e_ready = self.env.station_stock["east"]
        e_color = self.COLORS["stock_ready"] if e_ready else self.COLORS["stock_empty"]
        pygame.draw.rect(self.screen, self.COLORS["station_box"], (ex * cs + 4, ey * cs + 4, cs - 8, cs - 8), border_radius=4)
        pygame.draw.rect(self.screen, e_color, (ex * cs + 4, ey * cs + 4, cs - 8, cs - 8), 2, border_radius=4)
        self.screen.blit(self.label_font.render("DOGU AL", True, e_color), (ex * cs + 8, ey * cs + 12))
        self.screen.blit(self.sub_font.render("DOLU" if e_ready else "BEKLE", True, e_color), (ex * cs + 14, ey * cs + 34))

        # Teslimat noktalarını çiz
        edx, edy = self.env.EAST_DROPOFF
        pygame.draw.rect(self.screen, (30, 80, 130), (edx * cs + 5, edy * cs + 5, cs - 10, cs - 10), border_radius=4)
        self.screen.blit(self.label_font.render("DOGU", True, self.COLORS["text"]), (edx * cs + 14, edy * cs + 14))
        self.screen.blit(self.sub_font.render("TESLİM", True, self.COLORS["text"]), (edx * cs + 12, edy * cs + 32))

        wdx, wdy = self.env.WEST_DROPOFF
        pygame.draw.rect(self.screen, (150, 70, 20), (wdx * cs + 5, wdy * cs + 5, cs - 10, cs - 10), border_radius=4)
        self.screen.blit(self.label_font.render("BATI", True, self.COLORS["text"]), (wdx * cs + 14, wdy * cs + 14))
        self.screen.blit(self.sub_font.render("TESLİM", True, self.COLORS["text"]), (wdx * cs + 12, wdy * cs + 32))

    # Ajanları, taşıdıkları yükleri ve batarya doluluk çubuklarını ekrana çizer.
    def _draw_agents(self):
        cs = self.cs
        for a in self.env.agents:
            x, y = self.env.positions[a]
            cx, cy = x * cs + cs // 2, y * cs + cs // 2
            pygame.draw.circle(self.screen, self.COLORS[a], (cx, cy), 18)
            pygame.draw.circle(self.screen, self.COLORS["text"], (cx, cy), 20, 2)

            p_type = self.env.payload[a]
            if p_type == 1:
                pygame.draw.circle(self.screen, self.COLORS["load_w2e"], (cx, cy), 8)
            elif p_type == 2:
                pygame.draw.circle(self.screen, self.COLORS["load_e2w"], (cx, cy), 8)

            pct = max(0, self.env.batteries[a]) / 100.0
            color = (46, 204, 113) if pct > 0.5 else ((241, 196, 15) if pct > 0.25 else (231, 76, 60))
            pygame.draw.rect(self.screen, (0, 0, 0), (x * cs + 10, y * cs + 4, 40, 5))
            pygame.draw.rect(self.screen, color, (x * cs + 10, y * cs + 4, int(40 * pct), 5))

    # Ekranın alt kısmına ajanların batarya, yük, teslimat ve ödül bilgilerini içeren bilgi panelini çizer.
    def _draw_dashboard(self):
        py = self.env.height * self.cs
        pygame.draw.rect(self.screen, (16, 17, 20), (0, py, self.w, 70))
        pygame.draw.line(self.screen, self.COLORS["grid"], (0, py), (self.w, py), 2)

        p_desc = {0: "BOŞ", 1: "BATI->DOGU", 2: "DOGU->BATI"}
        for i, a in enumerate(["agv_0", "agv_1"]):
            info = f"[{a.upper()}] Batarya: %{self.env.batteries[a]:<5.1f} | Yük: {p_desc[self.env.payload[a]]:<10} | Teslimat: {self.env.deliveries[a]}/2 | Ödül: {self.env.total_rewards[a]:.0f} | Adım: {self.env.num_moves} | Çarp.: {self.env.collisions}"
            text = self.font.render(info, True, self.COLORS[a])
            self.screen.blit(text, (20, py + 12 + i * 26))
