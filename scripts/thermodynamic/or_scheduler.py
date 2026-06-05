# ORScheduler - extracted from termo2.py
"""
NLP2CMD - Przykłady zastosowań w różnych dziedzinach.

Ten moduł zawiera praktyczne przykłady użycia NLP2CMD
w IT, nauce i biznesie.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from operating_room import OperatingRoom
from surgery import Surgery

class ORScheduler:
    """
    Scheduler dla sal operacyjnych.

    Optymalizuje przydzielenie operacji do sal i czasów,
    uwzględniając ograniczenia sprzętowe i priorytet.
    """

    SETUP_TIME = 30  # Czas przygotowania sali (minuty)

    def __init__(self, rooms: list[OperatingRoom], surgeries: list[Surgery]):
        self.rooms = rooms
        self.surgeries = surgeries

    def _can_perform(self, room: OperatingRoom, surgery: Surgery) -> bool:
        """Sprawdź czy sala ma wymagany sprzęt."""
        return all(eq in room.equipment for eq in surgery.required_equipment)

    def schedule(self) -> dict[str, list[tuple[Surgery, int, int]]]:
        """
        Zaplanuj operacje.

        Returns:
            Dict: room_id -> [(surgery, start_time, end_time), ...]
        """
        sorted_surgeries = self._sort_surgeries_by_priority()
        schedule = self._initialize_schedule()
        room_end_times = self._get_room_end_times()

        for surgery in sorted_surgeries:
            best_room, best_start = self._find_best_room_for_surgery(
                surgery, room_end_times
            )
            
            if best_room:
                end_time = self._schedule_surgery_in_room(
                    schedule, best_room, surgery, best_start, room_end_times
                )

        return schedule
    
    def _sort_surgeries_by_priority(self) -> list[Surgery]:
        """Sortuj operacje wg priorytetu."""
        return sorted(self.surgeries, key=lambda s: s.priority)
    
    def _initialize_schedule(self) -> dict[str, list[tuple[Surgery, int, int]]]:
        """Inicjalizuj harmonogram."""
        return {room.id: [] for room in self.rooms}
    
    def _get_room_end_times(self) -> dict[str, int]:
        """Pobierz czasy zakończenia dla sal."""
        return {room.id: room.available_hours[0] * 60 for room in self.rooms}
    
    def _find_best_room_for_surgery(self, surgery: Surgery, room_end_times: dict[str, int]) -> tuple[Optional[OperatingRoom], int]:
        """Znajdź najlepszą salę dla operacji."""
        best_room = None
        best_start = float('inf')

        for room in self.rooms:
            if not self._can_perform(room, surgery):
                continue

            start = room_end_times[room.id] + self.SETUP_TIME
            room_end = room.available_hours[1] * 60

            if start + surgery.duration_min <= room_end:
                if start < best_start:
                    best_start = start
                    best_room = room

        return best_room, best_start
    
    def _schedule_surgery_in_room(self, schedule: dict[str, list[tuple[Surgery, int, int]]], 
                                room: OperatingRoom, surgery: Surgery, 
                                start_time: int, room_end_times: dict[str, int]) -> int:
        """Zaplanuj operację w sali."""
        end_time = start_time + surgery.duration_min
        schedule[room.id].append((surgery, start_time, end_time))
        room_end_times[room.id] = end_time
        return end_time

    def print_schedule(self, schedule: dict):
        """Wyświetl harmonogram."""
        for room_id, surgeries in schedule.items():
            print(f"\n   {room_id}:")
            for surgery, start, end in surgeries:
                start_h, start_m = divmod(start, 60)
                end_h, end_m = divmod(end, 60)
                print(f"      {start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d} "
                      f"{surgery.id} ({surgery.duration_min}min, P{surgery.priority})")
