# variabelen voor de graphical user interface

# enkele variabelen die gewoon per getal kunnen ingesteld worden
qe_min = "Minimal Elevation"
qe_max = "Maximal Elevation"
qh_min = "Minimal Horizontal Rotation"
qh_max = "Maximal Horizontal Rotation"
qh = [qh_min, qh_max, 0, 45, 60] # en alles daar tussen in, maar nu even wat dropdown standen 

# imiteren passieve Vari-A
min_motor = -4400 # default, kan aangepast worden naar meer
max_motor = 4400
startmotor_angle = 20 # default 65 graden, afhankelijk van waar voor de gebruiker prettig
endmotor_angle = 130 # default 120 graden, afhankelijk van waar voor de gebruiker prettig
middle_motor = 0 # default 0 graden, ook 0 steps, dan is de arm recht vooruit

# ondersteuningsprofiel 1 = E-Vari-A statisch ophogen, per qh verschillend instellen
upp_varia = 5 # default, dit moet een slider worden
start_support = startmotor_angle + 0 # default, dit moet een slider worden, vanaf welk punt de E-Vari-A statisch wordt opgehoogd

# ondersteuningsprofiel 2 = Boost, per qh verschillend instellen
start_boost = startmotor_angle + 0 # default, slider, zelfde als bij ondersteuningsprofiel 1
height_boost = 0 # default, ophogen om de E-vari-A overshoot in te stellen
gain_boost = 0 # default, ophogen om de snelheid van de boost in te stellen
# eindpunt boost nog een waarde geven? 


