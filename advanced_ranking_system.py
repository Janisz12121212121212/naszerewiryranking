import csv
import math
import json
from collections import defaultdict
from typing import Dict, List


class Player:
    def __init__(self, name: str):
        self.name = name
        self.impact = 1.0
        self.clutch_performance = defaultdict(int)


class Team:
    def __init__(self, name: str):
        self.name = name
        self.points = 1000
        self.match_history = []
        self.recent_matches = []
        self.map_performance = defaultdict(lambda: {"wins": 0, "losses": 0})
        self.heatmap_data = defaultdict(int)
        self.momentum_score = 0
        self.resilience_score = 0

    def update_points(self, delta: float):
        self.points += delta

    def add_match(self, match_details: Dict):
        self.match_history.append(match_details)
        self.recent_matches.append(match_details)
        if len(self.recent_matches) > 10:
            self.recent_matches.pop(0)

    def update_map_performance(self, map_name: str, result: str):
        if result == "win":
            self.map_performance[map_name]["wins"] += 1
        else:
            self.map_performance[map_name]["losses"] += 1

    def update_heatmap(self, position: str):
        self.heatmap_data[position] += 1


class Match:
    def __init__(self, team_a: Team, team_b: Team, score_a: int, score_b: int,
                 map_name: str = None, is_tournament: bool = False, stage: str = "Group Stage", positions_a=None, positions_b=None):
        self.team_a = team_a
        self.team_b = team_b
        self.score_a = score_a
        self.score_b = score_b
        self.map_name = map_name
        self.is_tournament = is_tournament
        self.stage = stage
        self.positions_a = positions_a or []
        self.positions_b = positions_b or []
        self.base_k_factor = 32

    def calculate_elo_change(self):
        stage_multiplier = {"Group Stage": 1.0, "Quarterfinal": 1.2, "Semifinal": 1.5, "Final": 2.0}
        k_factor = self.base_k_factor * stage_multiplier.get(self.stage, 1.0)

        expected_a = 1 / (1 + math.pow(10, (self.team_b.points - self.team_a.points) / 400))
        expected_b = 1 - expected_a

        actual_a = 1 if self.score_a > self.score_b else 0
        actual_b = 1 - actual_a

        score_difference = abs(self.score_a - self.score_b)
        k_factor *= 1 + (score_difference / 16)

        delta_a = k_factor * (actual_a - expected_a)
        delta_b = k_factor * (actual_b - expected_b)

        return delta_a, delta_b

    def apply_match_results(self):
        delta_a, delta_b = self.calculate_elo_change()

        self.team_a.update_points(delta_a)
        self.team_b.update_points(delta_b)

        self.team_a.add_match({
            "opponent": self.team_b.name,
            "score": self.score_a,
            "result": "win" if self.score_a > self.score_b else "loss",
            "map": self.map_name,
            "tournament": self.is_tournament,
            "stage": self.stage
        })
        self.team_b.add_match({
            "opponent": self.team_a.name,
            "score": self.score_b,
            "result": "win" if self.score_b > self.score_a else "loss",
            "map": self.map_name,
            "tournament": self.is_tournament,
            "stage": self.stage
        })

        self.team_a.update_map_performance(self.map_name, "win" if self.score_a > self.score_b else "loss")
        self.team_b.update_map_performance(self.map_name, "loss" if self.score_a > self.score_b else "win")

        for position in self.positions_a:
            self.team_a.update_heatmap(position)
        for position in self.positions_b:
            self.team_b.update_heatmap(position)


class RankingSystem:
    def __init__(self):
        self.teams = {}
        self.players = {}

    def get_or_create_team(self, team_name: str) -> Team:
        if team_name not in self.teams:
            self.teams[team_name] = Team(team_name)
        return self.teams[team_name]

    def get_or_create_player(self, player_name: str) -> Player:
        if player_name not in self.players:
            self.players[player_name] = Player(player_name)
        return self.players[player_name]

    def record_match(self, team_a_name: str, team_b_name: str, score_a: int, score_b: int,
                     map_name: str = None, is_tournament: bool = False, stage: str = "Group Stage",
                     positions_a=None, positions_b=None):
        team_a = self.get_or_create_team(team_a_name)
        team_b = self.get_or_create_team(team_b_name)
        match = Match(team_a, team_b, score_a, score_b, map_name, is_tournament, stage, positions_a, positions_b)
        match.apply_match_results()

    def normalize_rankings(self):
        average_points = sum(team.points for team in self.teams.values()) / len(self.teams)
        for team in self.teams.values():
            team.points += (1000 - average_points) * 0.1

    def get_rankings(self):
        sorted_teams = sorted(self.teams.values(), key=lambda x: x.points, reverse=True)
        return [{
            "team": team.name,
            "points": round(team.points, 2),
            "map_performance": team.map_performance,
            "heatmap": dict(team.heatmap_data)
        } for team in sorted_teams]

    def export_to_json(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(self.get_rankings(), f, indent=4)

    def load_matches_from_csv(self, csv_path: str):
        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                positions_a = row.get('positions_a', '').split(';') if 'positions_a' in row else []
                positions_b = row.get('positions_b', '').split(';') if 'positions_b' in row else []
                self.record_match(
                    team_a_name=row['team_a'],
                    team_b_name=row['team_b'],
                    score_a=int(row['score_a']),
                    score_b=int(row['score_b']),
                    map_name=row.get('map_name', None),
                    is_tournament=row.get('is_tournament', 'False').lower() == 'true',
                    stage=row.get('stage', 'Group Stage'),
                    positions_a=positions_a,
                    positions_b=positions_b
                )


if __name__ == "__main__":
    csv_file_path = "turniej_cs2_matches.csv"
    json_output_path = "ranking.json"

    ranking_system = RankingSystem()
    ranking_system.load_matches_from_csv(csv_file_path)
    ranking_system.normalize_rankings()
    ranking_system.export_to_json(json_output_path)

    print(f"Ranking data exported to {json_output_path}")
