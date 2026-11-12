"""Correções manuais das categorias do vocabulário do LVIS (data/vocabulario.csv).

A categoria automática (WordNet e, em último caso, o vizinho mais parecido no CLIP) erra
bastante: cenoura em "brinquedos e games", gaiola em "veículos", alicate em "calçados".
Aqui fica a correção por synset. None = remover (não é algo que se compra/come/adota,
ou só atrapalha o reconhecimento: avião, placa de rua, pessoa...).

Aplicado por scripts/gerar_vocabulario.py ao gerar o vocabulário e, sem precisar do CLIP,
direto sobre o CSV e os vetores já gerados:
    python scripts/correcoes_vocabulario.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

CASA = "casa e decoração"
ESPORTE = "esporte e lazer"
PAPEL = "livros e papelaria"
BRINQ = "brinquedos e games"
ELETRO = "eletrônicos"
VEST = "vestuário"

_REMOVER = """
airplane.n.01 ambulance.n.01 awning.n.01 balloon.n.01 barge.n.01 blimp.n.02 bullet_train.n.01 bus.n.01
cab.n.03 cabin_car.n.01 car.n.02 car.n.04 cargo_ship.n.01 carriage.n.02 coil.n.05 cruise_ship.n.01
cruiser.n.01 fighter.n.02 fire_engine.n.01 freight_car.n.01 garbage_truck.n.01 gondola.n.02 grill.n.02
helicopter.n.01 hot-air_balloon.n.01 houseboat.n.01 jet.n.01 knocker.n.05 license_plate.n.01
motor_vehicle.n.01 parking_meter.n.01 passenger_car.n.01 passenger_ship.n.01 power_shovel.n.01
river_boat.n.01 school_bus.n.01 seaplane.n.01 space_shuttle.n.01 stagecoach.n.01 stop_sign.n.01
tank.n.01 tow_truck.n.01 trailer_truck.n.01 train.n.01 bulldozer.n.01 wagon.n.01 plow.n.01
armor.n.01 award.n.02 billboard.n.01 brass.n.07 bulletin_board.n.02 cabinet.n.03 card.n.02 cast.n.05
checkbook.n.01 cigarette.n.01 crossbar.n.01 crumb.n.03 flagpole.n.02 flap.n.01 gravestone.n.01
heart.n.02 keycard.n.01 milestone.n.01 money.n.03 newsstand.n.01 passport.n.02 postbox.n.01
receipt.n.02 scarecrow.n.01 shield.n.02 signboard.n.01 street_sign.n.01 sword.n.01 top.n.09 vent.n.01
winker.n.02 medicine.n.02 syringe.n.01
backboard.n.01 bob.n.05 bolt.n.06 bow.n.04 buoy.n.01 cleat.n.02 coin.n.01 dagger.n.01 girdle.n.02
handle.n.01 knob.n.02 latch.n.02 log.n.01 mascot.n.01 peg.n.04 penny.n.02 pistol.n.01 pole.n.01
projectile.n.01 propeller.n.01 snowman.n.01 tag.n.02 tartan.n.01 weathervane.n.01 windsock.n.01
yoke.n.07 pinecone.n.01 seashell.n.01 statue.n.01 sculpture.n.01
antenna.n.01 bamboo.n.02 boom.n.04 chain_mail.n.01 control.n.09 dollar.n.02 fire_alarm.n.02
gasmask.n.01 gem.n.02 gun.n.01 machine_gun.n.01 mail_slot.n.01 manhole.n.01 mast.n.01 nest.n.01
noseband.n.01 person.n.01 pipe.n.02 radar.n.01 rifle.n.01 scoreboard.n.01 silo.n.01 solar_array.n.01
telephone_booth.n.01 telephone_pole.n.01 vending_machine.n.01 windmill.n.01 fireplace.n.01
base.n.03 cane.n.01 ferris_wheel.n.01 fire_hose.n.01 headstall.n.01 home_plate.n.01 mound.n.01
wagon_wheel.n.01 blinker.n.01 cabana.n.01 chute.n.02 cornice.n.01 gargle.n.01 pendulum.n.01
cowbell.n.01 pennant.n.02 sail.n.01 sling.n.05 spear.n.01 stirrup.n.01 gag.n.02 wine_bucket.n.01
"""

_MUDAR = {
    # veículos que ficam (coisas que se compram), mas com categoria certa
    "baby_buggy.n.01": BRINQ, "barrow.n.03": CASA, "birdcage.n.01": CASA, "car_battery.n.01": ELETRO,
    "drone.n.04": ELETRO, "handcart.n.01": CASA, "lawn_mower.n.01": CASA, "motor.n.01": ELETRO,
    "rearview_mirror.n.01": "veículos", "saddle.n.01": ESPORTE, "shopping_cart.n.01": CASA, "shovel.n.01": CASA,
    "skateboard.n.01": ESPORTE, "sled.n.01": ESPORTE, "steering_wheel.n.01": "veículos",
    "tricycle.n.01": BRINQ, "unicycle.n.01": ESPORTE, "wheel.n.01": "veículos",
    "windshield_wiper.n.01": "veículos", "bicycle.n.01": ESPORTE, "canoe.n.01": ESPORTE,
    "kayak.n.01": ESPORTE, "dinghy.n.01": ESPORTE, "water_scooter.n.01": ESPORTE, "golfcart.n.01": ESPORTE,
    "hairpin.n.01": "beleza",
    # livros e papelaria
    "bib.n.02": VEST, "bobby_pin.n.01": "beleza", "board.n.09": BRINQ, "cleansing_agent.n.01": CASA,
    "coaster.n.03": CASA, "cube.n.05": BRINQ, "dartboard.n.01": BRINQ, "doormat.n.02": CASA,
    "drumstick.n.02": ESPORTE, "fan.n.01": ELETRO, "file.n.04": CASA, "first-aid_kit.n.01": CASA,
    "fishing_rod.n.01": ESPORTE, "green_bean.n.02": "comida", "handkerchief.n.01": VEST, "handsaw.n.01": CASA,
    "heater.n.01": ELETRO, "hinge.n.01": CASA, "hourglass.n.01": CASA, "knife.n.01": CASA,
    "knitting_needle.n.01": CASA, "lanyard.n.02": VEST, "measuring_stick.n.01": CASA, "nailfile.n.01": "beleza",
    "napkin.n.01": CASA, "paper_towel.n.01": CASA, "peeler.n.03": CASA, "pitchfork.n.01": CASA,
    "pocketknife.n.01": CASA, "radiator.n.03": ELETRO, "razorblade.n.01": "beleza", "safety_pin.n.01": CASA,
    "scraper.n.01": CASA, "screwdriver.n.01": CASA, "ski_pole.n.01": ESPORTE, "straw.n.04": CASA,
    "sunflower.n.01": CASA, "tarpaulin.n.01": CASA, "tinfoil.n.01": CASA, "tissue.n.02": CASA,
    "toilet_tissue.n.01": CASA, "stylus.n.02": ELETRO,
    # brinquedos e games
    "almond.n.02": "comida", "ax.n.01": CASA, "bait.n.02": ESPORTE, "ball.n.06": ESPORTE,
    "baseball.n.02": ESPORTE, "basketball.n.02": ESPORTE, "bowling_ball.n.01": ESPORTE, "broom.n.01": CASA,
    "button.n.01": VEST, "carnation.n.01": CASA, "carrot.n.01": "comida", "celery.n.01": "comida",
    "chickpea.n.01": "comida", "clementine.n.01": "comida", "clip.n.03": PAPEL, "clothespin.n.01": CASA,
    "coat_hanger.n.01": CASA, "coconut.n.02": "comida", "comforter.n.04": BRINQ, "corkscrew.n.01": CASA,
    "detergent.n.01": CASA, "drill.n.01": CASA, "eraser.n.01": PAPEL, "football.n.02": ESPORTE,
    "gourd.n.02": "comida", "hairbrush.n.01": "beleza", "hose.n.03": CASA, "igniter.n.01": CASA,
    "key.n.01": CASA, "lettuce.n.02": "comida", "life_buoy.n.01": ESPORTE, "magnet.n.01": CASA,
    "mallet.n.01": CASA, "mushroom.n.02": "comida", "nut.n.03": CASA, "nutcracker.n.01": CASA,
    "onion.n.01": "comida", "paperweight.n.01": PAPEL, "parachute.n.01": ESPORTE, "pegboard.n.01": CASA,
    "pin.n.09": PAPEL, "ping-pong_ball.n.01": ESPORTE, "pipe.n.01": CASA, "poker.n.01": CASA,
    "pool_table.n.01": ESPORTE, "punch.n.03": PAPEL, "radish.n.03": "comida", "record_player.n.01": ELETRO,
    "rubber_band.n.01": PAPEL, "scissors.n.01": PAPEL, "scrub_brush.n.01": CASA, "skewer.n.01": CASA,
    "soap.n.01": "beleza", "soccer_ball.n.01": ESPORTE, "softball.n.01": ESPORTE, "sponge.n.01": CASA,
    "swab.n.02": CASA, "tennis_ball.n.01": ESPORTE, "thread.n.01": CASA, "thumbtack.n.01": PAPEL,
    "toothpaste.n.01": "beleza", "toothpick.n.01": CASA, "turnip.n.01": "comida", "volleyball.n.02": ESPORTE,
    # eletrônicos
    "birdhouse.n.01": CASA, "blackboard.n.01": PAPEL, "broccoli.n.01": "comida", "can_opener.n.01": CASA,
    "compass.n.01": ESPORTE, "crowbar.n.01": CASA, "dental_floss.n.01": "beleza",
    "dropper.n.01": CASA, "earplug.n.01": CASA, "flannel.n.01": VEST, "garden_hose.n.01": CASA,
    "hammer.n.02": CASA, "hand_glass.n.01": CASA, "headband.n.01": VEST, "kennel.n.01": CASA,
    "legume.n.02": "comida", "mirror.n.01": CASA, "shampoo.n.01": "beleza", "sharpener.n.01": PAPEL,
    "stirrer.n.02": CASA, "toilet.n.02": CASA, "tripod.n.01": ELETRO, "umbrella.n.01": VEST,
    "stapler.n.01": PAPEL, "binoculars.n.01": ESPORTE, "thermometer.n.01": CASA, "wall_socket.n.01": CASA,
    "phonograph_record.n.01": ELETRO, "videotape.n.01": ELETRO,
    # esporte e lazer
    "doorknob.n.01": CASA, "globe.n.03": PAPEL, "ironing_board.n.01": CASA, "walking_stick.n.01": ESPORTE,
    # calçados
    "band_aid.n.01": CASA, "bandage.n.01": CASA, "barrette.n.01": "beleza", "bell.n.01": CASA,
    "bolt.n.03": CASA, "checkerboard.n.01": BRINQ, "clasp.n.01": VEST, "freshener.n.01": CASA,
    "hook.n.05": CASA, "leather.n.01": VEST, "milkshake.n.01": "bebidas", "needle.n.03": CASA,
    "pad.n.04": CASA, "paddle.n.04": ESPORTE, "padlock.n.01": CASA, "pantyhose.n.01": VEST,
    "pliers.n.01": CASA, "racket.n.04": ESPORTE, "shaver.n.03": "beleza", "shears.n.01": CASA,
    "shredder.n.01": ELETRO, "ski.n.01": ESPORTE, "sparkler.n.02": CASA, "strap.n.01": VEST,
    "tights.n.01": VEST, "tongs.n.01": CASA, "wrench.n.03": CASA, "sock.n.01": VEST,
    # beleza
    "painting.n.01": CASA, "palette.n.02": PAPEL, "pepper_mill.n.01": CASA, "mask.n.04": VEST,
}

CORRECOES: dict[str, str | None] = {s: None for s in _REMOVER.split()} | _MUDAR


def aplicar(linhas: list[dict]) -> tuple[list[dict], list[int]]:
    """Corrige as categorias; devolve as linhas que ficam e os índices delas (para filtrar os vetores)."""
    from src.categorias import tipo_da_categoria

    ficam, indices = [], []
    for i, l in enumerate(linhas):
        if l["synset"] in CORRECOES:
            nova = CORRECOES[l["synset"]]
            if nova is None:
                continue
            l = {**l, "categoria": nova, "tipo": tipo_da_categoria(nova)}
        ficam.append(l)
        indices.append(i)
    return ficam, indices


if __name__ == "__main__":
    import numpy as np

    raiz = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz))
    csv_path, npy_path = raiz / "data/vocabulario.csv", raiz / "data/vocabulario_clip.npy"
    with open(csv_path, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    vetores = np.load(npy_path)
    assert len(vetores) == len(linhas)
    ficam, indices = aplicar(linhas)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rotulo_en", "nome", "categoria", "tipo", "synset"], lineterminator="\n")
        w.writeheader()
        w.writerows(ficam)
    np.save(npy_path, vetores[indices])
    print(f"{len(linhas)} -> {len(ficam)} rótulos")
