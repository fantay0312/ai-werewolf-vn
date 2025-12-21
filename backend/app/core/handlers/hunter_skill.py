from app.core.phase_handler import PhaseHandler
from app.models.game_state import GamePhase, ActionType, GameLog, Role
from app.models.action_model import ActionRequest
import uuid

class HunterSkillHandler(PhaseHandler):
    def get_phase(self) -> GamePhase:
        return GamePhase.HUNTER_SKILL

    def on_enter(self):
        # Identify who can shoot
        # This handler assumes we entered because SOMEONE died who can shoot.
        # We need to find that player.
        # In a complex scenario, multiple people might die.
        # For MVP, let's handle one shooter at a time.
        # The game state should probably track "pending_skill_users" queue?
        # Or we just iterate and find the first dead hunter/wolf_king who hasn't used skill AND wasn't poisoned.
        
        shooter = self._find_shooter()
        if shooter:
            role_name = "猎人" if shooter.role == Role.HUNTER else "狼王"
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{shooter.id}号玩家({role_name})死亡，请选择是否发动技能开枪带人。",
                is_public=True
            )
            self.game.game_logs.append(log)
            
            # Reset action for this player
            shooter.has_acted = False
        else:
            # No one to shoot? Should not happen if logic is correct, but safe fallback
            pass

    def process_action(self, action: ActionRequest) -> bool:
        player = next((p for p in self.game.players if p.id == action.player_id), None)
        if not player:
            return False
            
        # Verify if this player is the current allowed shooter
        shooter = self._find_shooter()
        if not shooter or player.id != shooter.id:
            return False

        if action.type == ActionType.SHOOT:
            target = next((p for p in self.game.players if p.id == action.target_id), None)
            if not target or not target.is_alive:
                return False
                
            # Kill target
            target.is_alive = False
            self.game.dead_players.append(target.id)
            player.gun_used = True
            player.has_acted = True
            
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号玩家开枪带走了{target.id}号玩家。",
                is_public=True
            )
            self.game.game_logs.append(log)
            
            return True
            
        elif action.type == ActionType.PASS:
            player.gun_used = True # Mark as used/forfeited
            player.has_acted = True
            
            log = GameLog(
                id=str(uuid.uuid4()),
                day=self.game.day,
                phase=self.game.phase,
                content=f"{player.id}号玩家选择不开枪。",
                is_public=True
            )
            self.game.game_logs.append(log)
            return True
            
        return False

    def try_advance(self) -> GamePhase:
        shooter = self._find_shooter()
        if not shooter:
            # No more shooters, where to go?
            # We need to resume the game flow.
            # This is tricky because we could have come from Night Resolve or Day Vote.
            # And the shot player might trigger THEIR skill (e.g. Wolf King shot by Hunter).
            # Or Sheriff might have died.
            
            # 1. Check if another shooter exists (recursion/loop)
            # If _find_shooter returns None, it means no one pending.
            
            # 2. Check for Sheriff Transfer
            # If any dead player was Sheriff, go to Sheriff Transfer
            dead_sheriff = next((p for p in self.game.players if not p.is_alive and p.is_sheriff), None)
            if dead_sheriff:
                # We need to handle sheriff transfer.
                # But wait, if sheriff died earlier, we might have already handled it?
                # We need a flag "sheriff_transfer_pending"?
                # Or just check if sheriff is dead and badge is not transferred?
                # Let's assume SheriffTransferHandler handles the logic of "has acted".
                return GamePhase.SHERIFF_TRANSFER
            
            # 3. Resume normal flow
            # If it was Night (day=X, phase=NightResolve -> HunterSkill), we go to DayStart?
            # Actually NightResolve transitions to DayStart.
            # So if we interrupted NightResolve, we should go to DayStart.
            # If we came from DayVoteResult, we should go to NightStart (or GameEnd).
            
            # We can infer based on time of day?
            # Or store "next_phase" in GameState?
            # For MVP, let's assume:
            # If it's Day 1+ and we are in HunterSkill, it's likely after Vote or Night.
            # If we just finished Night Resolve, we want Day Start (or Sheriff Election).
            # If we just finished Day Vote, we want Night Start.
            
            # Heuristic:
            # If game.wolf_kill_target is set (meaning we came from night), go to Day Start.
            # Wait, wolf_kill_target is cleared?
            # Let's use a simpler heuristic:
            # If we are handling death skills, we are technically still resolving the previous phase's result.
            # But we don't know which one easily without state.
            # Let's default to:
            # If current time is "Day", go to Night.
            # If current time is "Night" (transitioning to day), go to Day.
            
            # Actually, NightResolve sets phase to DAY_START.
            # So if we intercepted that, we are technically in Day.
            # But wait, `NightResolveHandler` returns `DAY_START`.
            # If we change that to return `HUNTER_SKILL`, then we are in `HUNTER_SKILL`.
            # After `HUNTER_SKILL`, we should go to `DAY_START` (to announce results/continue) or `DAY_DISCUSS`.
            
            # Let's assume:
            # If we are in `HUNTER_SKILL`, we always go to `SHERIFF_TRANSFER` (checked above) or...
            # If we came from Night, we want to go to `DAY_DISCUSS` (or `SHERIFF_ELECTION` on Day 1).
            # If we came from Day Vote, we want to go to `NIGHT_START`.
            
            # How to distinguish?
            # Maybe check `game.game_logs` last phase?
            # Or add `return_phase` to GameState.
            
            # For now, let's assume we go to `DAY_DISCUSS` if it's early in the day, or `NIGHT_START` if it's late.
            # But wait, Day Vote happens at end of day.
            # So if we are here, it's likely Day Vote Result -> Death -> Skill.
            # So next is Night.
            
            # BUT, if Night Resolve -> Death -> Skill.
            # Next is Day Discuss.
            
            # Let's check `game.day`.
            # If we are in Night Resolve, day is incremented?
            # `NightResolveHandler` does NOT increment day. `DayVoteResultHandler` increments day.
            # Wait, `DayVoteResultHandler` increments day BEFORE returning `NIGHT_START`.
            
            # So if we are in `HUNTER_SKILL`:
            # If we came from Night Resolve, day is same as night.
            # If we came from Day Vote, day is same as day.
            
            # This is ambiguous.
            # Let's add `next_phase` to GameState to know where to return.
            if hasattr(self.game, 'next_phase_after_skill') and self.game.next_phase_after_skill:
                return self.game.next_phase_after_skill
            
            return GamePhase.DAY_DISCUSS # Fallback
            
        return None

    def _find_shooter(self):
        # Find a player who:
        # 1. Is dead
        # 2. Is Hunter or Wolf King
        # 3. Has NOT used gun (gun_used=False)
        # 4. Was NOT poisoned (poisoned_by_witch=False)
        # 5. Has NOT acted in this skill phase (has_acted=False) - wait, we reset this in on_enter?
        #    No, we need to find someone who NEEDS to act.
        
        # We need to be careful about "has_acted".
        # If we have multiple shooters, we handle them one by one.
        # The one currently handling should have has_acted=False.
        # The ones already handled should have has_acted=True (or gun_used=True).
        
        for p in self.game.players:
            if not p.is_alive and p.role in [Role.HUNTER, Role.WOLF_KING]:
                if not p.gun_used and not p.poisoned_by_witch:
                    # Check if they have already acted in this phase?
                    # If we stay in HUNTER_SKILL phase for multiple shooters,
                    # we need to distinguish "waiting to shoot" vs "already passed".
                    # If they passed, gun_used should be True.
                    # So if gun_used is False, they are a candidate.
                    return p
        return None