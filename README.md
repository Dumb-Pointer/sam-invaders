# Rocket vs Robots

Run with `uv run game`.

Level 1 has slower robots (80 pixels per second) and no bombs.
Defeating Level 1’s army and boss starts Level 2 with 36 faster robots (110 pixels per
second), a fresh shield, and no bombs. Defeating Level 2’s boss starts
Level 3: 36 robots at the same speed, now dropping bombs. Defeating Level 3’s boss starts Level 4 with the same 36 robots, bombs, and goodies,
but twice the robot speed (220 pixels per second). Defeating Level 4’s boss starts Level 5 at twice its speed (440 pixels per second).
Defeat Level 5’s boss to win.
Each new level restores your shield. A direct nuclear bomb hit destroys the rocket even with a full shield.
Nuclear bombs drop roughly every 4–7 seconds; goodies keep their regular pace.

Use `uv run game --level 3` to test Level 3 directly (or `--level 2` for Level 2).

- Player 1 (blue): Left/Right arrows move; Up shoots.
- Player 2 (orange): Z/C move; X shoots.
- Only one missile can be on screen at a time. Fire again after it hits a robot or leaves the screen.
- Clear 40 robots in Level 1 (10 columns, 4 rows) and 36 in Levels 2, 3, 4, and 5 (9 columns, 4 rows). Each robot takes one missile hit.
- The formation moves sideways, drops one step at the edge, then reverses.
- Your shield absorbs three collisions, losing a visible segment each time.
- Shield hits destroy the colliding robot and give a short grace period.
- After the shield breaks, another collision destroys the rocket.
- Three robot hits break a full shield; the fourth destroys the rocket. Robots
  that pass the bottom return to the top instead of causing an instant loss.
- Press R to restart from your chosen starting level, or Esc to quit.

Arcade sound effects play for shots, explosions, shield impacts, fleet drops,
and winning or losing. Press M to mute/unmute. Sounds are synthesized locally;
no downloaded assets are required. Robot hits also create explosion particles.

## Demo mode

Run `uv run game --demo` to watch the autopilot play.
Press D at any time to switch between demo and manual controls.
The autopilot moves and fires through the same rules as the player.
Press R to restart the demo from your chosen starting level.

## Level 3 goodies

Every third robot drop is a collectible instead of a bomb. Catch it with your
rocket. Regular types cycle through rapid fire, shield, laser, and buddies.
The drone is a separate, one-time rescue drop:

- **D — Crazy drone:** only one drops per Level 3 attempt, after 20 seconds or
  when nine robots remain. Catch it to save a charge. Player 1 presses **Right Shift**,
  Player 2 presses **V** to activate it whenever needed. A 48-propeller drone sprays
  8 glowing fireflies in all directions every 1.2 seconds for 6 seconds, with an
  original robotic pop melody.
  Fireflies destroy robots and never damage either player.
- **F — Rapid fire:** for 10 seconds, hold your shoot key to fire every 0.16 seconds,
  with up to six missiles in flight. Normal shooting remains one missile per press.
- **+ — Shield:** repairs one segment, up to three.
- **L — Laser:** for 10 seconds, your shoot key fires a beam that destroys every robot
  and bomb along its vertical line. Combines with rapid fire.
- **B — Buddies:** two orbiting rockets automatically fire for 12 seconds.

Collecting the same temporary power refreshes its timer. Active powers and
remaining seconds appear at the top. Restarting or changing level clears powers.

## Two-player co-op

Two players share the keyboard by default. Each has their own three-part shield,
one-missile limit, and power timers. Goodies affect the player who catches them.
If one rocket is destroyed, the teammate can continue; the game ends when both
are destroyed. Both return for the next level.
Press R to restart both players. Press D to let the demo pilot both rockets.

Run `uv run game --players 1` for one player, or
`uv run game --players 2 --level 3` to test co-op with bombs and goodies.

Level 3 bombs are chunky yellow cartoon nuclear bombs with radiation markings.
They have matching larger collision boxes and destroy a rocket on direct impact.
Pink spiral lollipops now appear among the goodies: catching one repairs one
shield segment (up to three) for the player who catches it.

Nuclear bombs are now twice as wide and tall (68 × 108 pixels). A direct rocket hit
is fatal even with a full shield. Hitting a rocket or reaching the bottom
creates a short, local mushroom cloud with a deep boom. The cloud is visual
only: it causes no splash damage and never expands to fill the screen.

## Goodie playground

Run `uv run game --playground` for an interactive test mode. Click Player 1 or Player 2,
then click a goodie/weapon button (or press 1–9) to see it immediately. Missiles,
rapid fire, and lasers fire automatically; buddies and drones activate at once.
Test rockets start with no shield. Shield repair and lollipop buttons instantly
add one segment to the selected rocket, up to three. Press 9 or click Remove
shield to remove its shield again. Resetting or reviving a test rocket starts
it without a shield. The bomb
button demonstrates rocket and floor explosions with normal game damage.

Robots stay still and respawn, enemy drops are disabled, and damage works exactly as it does in the game. Nuclear hits are fatal, even
with a full shield. Click another effect to revive its selected player, or reset
to revive both players. Click an effect again to repeat it. Press 0 or R to reset, M to mute,
and Esc to exit. Regular movement and shooting controls also work.

In the game, click **1 Player** or **2 Players** at the top right to choose
how many rockets to use. Switching restarts the current level with fresh rockets.
Restarting remembers your selected player count. Solo uses the arrow controls.

Level 5 grants double missiles to both players. Tap Up (Player 1) or X (Player 2)
to fire two missiles side by side. Wait until the volley clears before firing
again. Level 5 has no rapid fire, including from rapid-fire goodies.

Level 5 gives each rocket four shield segments, including a four-segment repair
limit. Four robot hits break the shield; the fifth destroys the rocket. Levels
1–4 keep three shield segments. Nuclear bomb hits remain fatal in every level.

Testing mode also has **3 Shields** and **4 Shields** buttons beneath the player
selector. They fill the selected rocket's shield and set its repair limit.
Remove shield still empties it, and Shield repair adds one segment at a time.
These selectors do not change normal game levels.

## Boss battles

Clear each robot army to summon its boss before advancing. Boss health equals
the full army size times the level: 40, 72, 108, 144, and 180 HP. Each later boss
moves faster, attacks more frequently, and fires more projectiles. Red boss
bolts remove one shield segment; bosses 3–5 also drop fatal nuclear bombs.
Missiles, buddy bullets, and fireflies each deal 1 damage; lasers deal 3.
Defeat Boss 5 to win. Powers collected during the wave carry into its boss fight.

In testing mode, click **Boss: 1–5** below the effect buttons to summon that
level's real boss. It has the same health, attacks, and damage as in the game.
Choose shields and weapons with the existing buttons. Reset returns to the
regular target playground.

Run boss regression checks with `uv run python -m unittest discover -s tests`.

Player 1 can also use Space to shoot while steering with Left/Right. Up still
works, and Player 2 still uses Z/C and X. Normal firing remains one press per
volley. For a boss waiting screen, run `uv run game --level 1 --boss --paused`;
combat begins only after clicking Start fight or pressing Enter.

Each player has three lives. A fatal hit consumes one life; surviving lives respawn
with a full shield (three segments, or four in Level 5) and two seconds of protection.
Lives carry across levels; a rocket stays out after its last life is lost.
The HUD shows lives and shields separately. Testing mode uses the same life rules.
Click Pause/Resume on screen, or press P, to freeze/resume gameplay in either mode.

**I — Invincibility** is now a falling goodie: eight seconds of complete damage
protection, including nuclear bombs. A gold ring and countdown show when it is
active. In the playground, click Invincibility or press I to try it directly.

Pause is keyboard-only: **P** toggles pause and resume in both game and testing
mode. On-screen Pause/Resume buttons have been removed. Pausing freezes power
timers too. The ready screen also accepts P to start.

A dancing old man appears once per level, sings “Gradili lia kilia,” then follows
with “Pecal” в нея скумрия. The two-line performance uses bundled synthesized
voice audio, with matching speech bubbles. He has no collision or damage effects.
In testing mode, click **O — Singing old man** or press O to replay the performance.
