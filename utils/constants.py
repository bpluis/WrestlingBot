# Game Constants for WWE Wrestling Bot
from typing import Dict, List
import random

# Archetypes with their characteristics
ARCHETYPES = {
    "Giant": {
        "description": "Massive wrestlers with incredible strength but limited agility",
        "height_range": {
            "Male": (6.5, 7.2),
            "Female": (6.0, 6.7)
        },
        "strength_bonus": 15,
        "durability_bonus": 10,
        "agility_penalty": -15,
        "speed_penalty": -10
    },
    "High Flyer": {
        "description": "Agile aerial specialists with high-risk, high-reward offense",
        "height_range": {
            "Male": (5.5, 6.0),
            "Female": (5.0, 5.5)
        },
        "aerial_bonus": 15,
        "agility_bonus": 10,
        "speed_bonus": 10,
        "strength_penalty": -10,
        "durability_penalty": -10
    },
    "Technical": {
        "description": "Balanced ring generals who excel at counters and technique",
        "height_range": {
            "Male": (5.8, 6.3),
            "Female": (5.3, 5.8)
        },
        "technical_bonus": 10,
        "reversal_bonus": 5,
        "balanced": True
    },
    "Striker": {
        "description": "High-volume offense specialists with devastating strikes",
        "height_range": {
            "Male": (5.7, 6.2),
            "Female": (5.2, 5.7)
        },
        "strike_bonus": 12,
        "speed_bonus": 8,
        "stamina_bonus": 5
    },
    "Powerhouse": {
        "description": "Strength specialists with well-rounded physical attributes",
        "height_range": {
            "Male": (6.0, 6.5),
            "Female": (5.5, 6.0)
        },
        "strength_bonus": 12,
        "power_bonus": 10,
        "stamina_bonus": 5,
        "agility_bonus": 3
    }
}

# Weight Classes
WEIGHT_CLASSES = [
    "Cruiser",      # Under 205 lbs
    "Light",        # 205-225 lbs
    "Heavy",        # 225-265 lbs
    "Superheavy",   # 265-325 lbs
    "Ultraheavy"    # 325+ lbs
]

# Persona restrictions based on Archetype, Weight, Alignment
# Format: persona_name: {archetypes: [], weights: [], alignments: []}
PERSONA_RESTRICTIONS = {
    "American Power": {
        "archetypes": ["Giant", "Powerhouse", "Striker", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face"]  # Face only!
    },
    "Fighter": {
        "archetypes": ["Powerhouse"],
        "weights": ["Cruiser", "Light", "Heavy"],
        "alignments": ["Face", "Heel"]
    },
    "Giant": {
        "archetypes": ["Powerhouse", "Giant"],
        "weights": ["Superheavy", "Ultraheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Grappler": {
        "archetypes": ["Powerhouse"],
        "weights": ["Cruiser", "Light", "Heavy"],
        "alignments": ["Face", "Heel"]
    },
    "Ground": {
        "archetypes": ["Powerhouse", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Heel": {
        "archetypes": ["Giant", "Powerhouse", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Heel"]  # Heel only!
    },
    "Junior": {
        "archetypes": ["High Flyer", "Technical"],
        "weights": ["Cruiser", "Light"],
        "alignments": ["Face", "Heel"]
    },
    "Luchador": {
        "archetypes": ["High Flyer", "Striker", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Mysterious": {
        "archetypes": ["Striker", "Technical"],
        "weights": ["Cruiser", "Light"],
        "alignments": ["Face", "Heel"]
    },
    "Orthodox": {
        "archetypes": ["Giant", "High Flyer", "Striker", "Technical", "Powerhouse"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy", "Ultraheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Panther": {
        "archetypes": ["High Flyer", "Striker", "Technical"],
        "weights": ["Cruiser", "Light"],
        "alignments": ["Face", "Heel"]
    },
    "Power": {
        "archetypes": ["Giant", "High Flyer", "Striker", "Technical", "Powerhouse"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy", "Ultraheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Shooter": {
        "archetypes": ["Powerhouse", "Striker", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Technician": {
        "archetypes": ["High Flyer", "Striker", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Vicious": {
        "archetypes": ["Giant", "Striker", "Technical", "Powerhouse"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face", "Heel"]
    },
    "Wrestling": {
        "archetypes": ["Powerhouse", "Striker", "Technical"],
        "weights": ["Cruiser", "Light", "Heavy", "Superheavy"],
        "alignments": ["Face", "Heel"]
    }
}

def get_available_personas(archetype: str, weight_class: str, alignment: str) -> List[str]:
    """Get available personas based on wrestler characteristics"""
    available = []
    
    for persona_name, restrictions in PERSONA_RESTRICTIONS.items():
        # Check archetype
        if archetype not in restrictions["archetypes"]:
            continue
        
        # Check weight class
        if weight_class not in restrictions["weights"]:
            continue
        
        # Check alignment with special Tweener rules
        if alignment == "Tweener":
            # Tweeners can use Face or Heel personas
            # EXCEPT: "American Power" (Face only) and "Heel" (Heel only)
            if persona_name in ["American Power", "Heel"]:
                continue
            # If persona allows Face or Heel, it's available for Tweener
            if "Face" in restrictions["alignments"] or "Heel" in restrictions["alignments"]:
                available.append(persona_name)
        else:
            # Face or Heel: must match exactly
            if alignment in restrictions["alignments"]:
                available.append(persona_name)
    
    return available

BODY_TYPES = {
    "Athletic": "Lean and toned physique",
    "Muscular": "Well-defined, bodybuilder-like build",
    "Powerlifter": "Thick, strong build with some bulk",
    "Average Build": "Everyday physique with some mass",
    "Lean": "Slim and agile frame",
    "Heavyweight": "Large, imposing frame with mass"
}

# In-Ring Personas/Styles
PERSONAS = {
    "American Power": {
        "description": "Patriotic, powerful, crowd-driven",
        "bonus_attrs": {
            "Strength": 5,
            "Grapple Offense": 5
        }
    },

    "Fighter": {
        "description": "Strike-heavy, tough, never backs down",
        "bonus_attrs": {
            "Running Offense": 5,
            "Head Durability": 5
        }
    },

    "Giant": {
        "description": "Massive powerhouse, hard to take down",
        "bonus_attrs": {
            "Strength": 8,
            "Pin Escape": 5
        }
    },

    "Grappler": {
        "description": "Clinch-focused, control-oriented",
        "bonus_attrs": {
            "Grapple Offense": 7,
            "Grapple Reversal": 5
        }
    },

    "Ground": {
        "description": "Submission specialist, mat-based wrestling",
        "bonus_attrs": {
            "Power Submission": 7,
            "Technical Submission": 7
        }
    },

    "Heel": {
        "description": "Cunning, rule-breaking, opportunistic",
        "bonus_attrs": {
            "Pin Escape": 5,
            "Recovery": 5
        }
    },

    "Junior": {
        "description": "Lightweight, quick, energetic",
        "bonus_attrs": {
            "Agility": 7,
            "Movement Speed": 5
        }
    },

    "Luchador": {
        "description": "High-flying masked wrestler",
        "bonus_attrs": {
            "Aerial Offense": 10,
            "Aerial Range": 5
        }
    },

    "Mysterious": {
        "description": "Unpredictable, mystical, enigmatic",
        "bonus_attrs": {
            "Agility": 5,
            "Special": 5
        }
    },

    "Orthodox": {
        "description": "Classic, traditional wrestling style",
        "bonus_attrs": {
            "Grapple Offense": 5,
            "Stamina": 5
        }
    },

    "Panther": {
        "description": "Agile, predatory instincts",
        "bonus_attrs": {
            "Agility": 7,
            "Movement Speed": 5
        }
    },

    "Power": {
        "description": "Explosive strength-based offense",
        "bonus_attrs": {
            "Arm Power": 5,
            "Leg Power": 5
        }
    },

    "Shooter": {
        "description": "MMA-influenced, strike-focused",
        "bonus_attrs": {
            "Running Offense": 5,
            "Strength": 5
        }
    },

    "Technician": {
        "description": "Precise, methodical, technical mastery",
        "bonus_attrs": {
            "Technical Submission": 8,
            "Grapple Reversal": 5
        }
    },

    "Vicious": {
        "description": "Brutal, relentless, merciless",
        "bonus_attrs": {
            "Strike Reversal": 5,
            "Head Durability": 5
        }
    },

    "Wrestling": {
        "description": "Well-rounded professional wrestler",
        "bonus_attrs": {
            "Stamina": 5,
            "Recovery": 5
        }
    }
}

# Personality Traits (Range: -100 to +100)
PERSONALITY_TRAITS = {
    "Prideful_Egotistical": {
        "name": "Prideful ↔ Egotistical",
        "description": "Prideful: Confident but fair. Egotistical: Won't play fair, taunts more",
        "negative": "Egotistical",
        "positive": "Prideful"
    },
    "Respectful_Disrespectful": {
        "name": "Respectful ↔ Disrespectful",
        "description": "Respectful: Handshakes, sportsmanship. Disrespectful: Attacks, insults",
        "negative": "Disrespectful",
        "positive": "Respectful"
    },
    "Perseverant_Desperate": {
        "name": "Perseverant ↔ Desperate",
        "description": "Perseverant: Follows rules. Desperate: Uses weapons when losing",
        "negative": "Desperate",
        "positive": "Perseverant"
    },
    "Loyal_Treacherous": {
        "name": "Loyal ↔ Treacherous",
        "description": "Loyal: Won't betray allies. Treacherous: Turns on partners",
        "negative": "Treacherous",
        "positive": "Loyal"
    },
    "Bold_Cowardly": {
        "name": "Bold ↔ Cowardly",
        "description": "Bold: Brings the fight. Cowardly: Runs away, gets counted out",
        "negative": "Cowardly",
        "positive": "Bold"
    },
    "Disciplined_Aggressive": {
        "name": "Disciplined ↔ Aggressive",
        "description": "Disciplined: Prefers ring fighting. Aggressive: Attacks before/after matches",
        "negative": "Aggressive",
        "positive": "Disciplined"
    }
}

# All attributes in WWE 2K25
ATTRIBUTES = [
    "Arm Power",
    "Leg Power",
    "Grapple Offense",
    "Running Offense",
    "Aerial Offense",
    "Aerial Range",
    "Power Submission",
    "Technical Submission",
    "Strike Reversal",
    "Grapple Reversal",
    "Aerial Reversal",
    "Head Durability",
    "Arm Durability",
    "Leg Durability",
    "Power Submission Defense",
    "Technical Submission Defense",
    "Pin Escape",
    "Strength",
    "Stamina",
    "Agility",
    "Movement Speed",
    "Recovery",
    "Special",
    "Finisher"
]

# Finisher/Signature Move Categories with complete move lists
MOVE_CATEGORIES = {
    "Grapples & Power Moves": {
        "emoji": "💪",
        "moves": {
            "Finishers": [
                "Powerbomb",
                "Sit-Out Powerbomb",
                "Pop-Up Powerbomb",
                "Running Powerslam",
                "Spinebuster",
                "Gorilla Press Slam",
                "Military Press Drop",
                "Uranage",
                "Sidewalk Slam",
                "Chokeslam",
                "Inverted Powerslam",
                "Scoop Slam",
                "Michinoku Driver",
                "Fireman's Carry Slam",
                "Death Valley Driver",
                "Release German Suplex",
                "Belly-to-Belly Suplex",
                "Exploder Suplex",
                "Back Body Drop",
                "Falcon Arrow",
                "Sit-Out Spinebuster",
                "High-Angle Slam",
                "Pumphandle Slam",
                "Overhead Belly-to-Belly",
                "Spinning Side Slam"
            ],
            "Signatures": [
                "Powerbomb",
                "Sit-Out Powerbomb",
                "Pop-Up Powerbomb",
                "Running Powerslam",
                "Spinebuster",
                "Gorilla Press Slam",
                "Military Press Drop",
                "Uranage",
                "Sidewalk Slam",
                "Chokeslam",
                "Inverted Powerslam",
                "Scoop Slam",
                "Michinoku Driver",
                "Fireman's Carry Slam",
                "Death Valley Driver",
                "Release German Suplex",
                "Belly-to-Belly Suplex",
                "Exploder Suplex",
                "Back Body Drop",
                "Falcon Arrow",
                "Sit-Out Spinebuster",
                "High-Angle Slam",
                "Pumphandle Slam",
                "Overhead Belly-to-Belly",
                "Spinning Side Slam"
            ]
        }
    },
    "Strikes": {
        "emoji": "👊",
        "moves": {
            "Finishers": [
                "Superkick",
                "Spinning Back Kick",
                "Running Knee Strike",
                "Jumping Knee Strike",
                "Roundhouse Kick",
                "Spinning Heel Kick",
                "Bicycle Kick",
                "Forearm Smash",
                "Discus Forearm",
                "European Uppercut",
                "Palm Strike",
                "Elbow Smash",
                "Spinning Elbow",
                "Short-Arm Headbutt",
                "Running Big Boot",
                "Jumping High Kick",
                "Leg Kick Combination",
                "Backfist Strike",
                "Rolling Elbow Strike",
                "Thrust Kick",
                "Snap Kick",
                "Knee Lift",
                "Corner High Kick",
                "Hammerfist Strike",
                "Double Palm Strike"
            ],
            "Signatures": [
                "Superkick",
                "Spinning Back Kick",
                "Running Knee Strike",
                "Jumping Knee Strike",
                "Roundhouse Kick",
                "Spinning Heel Kick",
                "Bicycle Kick",
                "Forearm Smash",
                "Discus Forearm",
                "European Uppercut",
                "Palm Strike",
                "Elbow Smash",
                "Spinning Elbow",
                "Short-Arm Headbutt",
                "Running Big Boot",
                "Jumping High Kick",
                "Leg Kick Combination",
                "Backfist Strike",
                "Rolling Elbow Strike",
                "Thrust Kick",
                "Snap Kick",
                "Knee Lift",
                "Corner High Kick",
                "Hammerfist Strike",
                "Double Palm Strike"
            ]
        }
    },
    "Submissions": {
        "emoji": "🔒",
        "moves": {
            "Finishers": [
                "Sleeper Hold",
                "Rear Naked Choke",
                "Crossface",
                "Armbar",
                "Triangle Choke",
                "Guillotine Choke",
                "Kimura Lock",
                "Ankle Lock",
                "Heel Hook",
                "Boston Crab",
                "Single-Leg Crab",
                "Sharpshooter-Style Leg Lock",
                "Cloverleaf",
                "STF",
                "Dragon Sleeper",
                "Camel Clutch",
                "Octopus Hold",
                "Fujiwara Armbar",
                "Knee Bar",
                "Stretch Muffler",
                "Abdominal Stretch",
                "Surfboard Stretch",
                "Leg Trap Choke",
                "Standing Arm Lock",
                "Modified Figure-Four Leg Lock"
            ],
            "Signatures": [
                "Sleeper Hold",
                "Rear Naked Choke",
                "Crossface",
                "Armbar",
                "Triangle Choke",
                "Guillotine Choke",
                "Kimura Lock",
                "Ankle Lock",
                "Heel Hook",
                "Boston Crab",
                "Single-Leg Crab",
                "Sharpshooter-Style Leg Lock",
                "Cloverleaf",
                "STF",
                "Dragon Sleeper",
                "Camel Clutch",
                "Octopus Hold",
                "Fujiwara Armbar",
                "Knee Bar",
                "Stretch Muffler",
                "Abdominal Stretch",
                "Surfboard Stretch",
                "Leg Trap Choke",
                "Standing Arm Lock",
                "Modified Figure-Four Leg Lock"
            ]
        }
    },
    "Aerial/High-Flying": {
        "emoji": "🦅",
        "moves": {
            "Finishers": [
                "Frog Splash",
                "Diving Splash",
                "Diving Elbow Drop",
                "Diving Leg Drop",
                "Moonsault",
                "Standing Moonsault",
                "Shooting Star Press",
                "Split-Legged Moonsault",
                "Springboard Splash",
                "Springboard Cutter",
                "Diving Crossbody",
                "Flying Body Press",
                "Corkscrew Splash",
                "Rolling Thunder",
                "Swanton-Style Dive",
                "Top Rope Senton",
                "Springboard Moonsault",
                "Diving Double Foot Stomp",
                "Top Rope Knee Drop",
                "Springboard Back Elbow",
                "Flying Forearm",
                "Tornado Splash",
                "Top Rope Splash Press",
                "Running Shooting Star",
                "Diving Back Splash"
            ],
            "Signatures": [
                "Frog Splash",
                "Diving Splash",
                "Diving Elbow Drop",
                "Diving Leg Drop",
                "Moonsault",
                "Standing Moonsault",
                "Shooting Star Press",
                "Split-Legged Moonsault",
                "Springboard Splash",
                "Springboard Cutter",
                "Diving Crossbody",
                "Flying Body Press",
                "Corkscrew Splash",
                "Rolling Thunder",
                "Swanton-Style Dive",
                "Top Rope Senton",
                "Springboard Moonsault",
                "Diving Double Foot Stomp",
                "Top Rope Knee Drop",
                "Springboard Back Elbow",
                "Flying Forearm",
                "Tornado Splash",
                "Top Rope Splash Press",
                "Running Shooting Star",
                "Diving Back Splash"
            ]
        }
    },
    "Lariats/Clotheslines": {
        "emoji": "🥋",
        "moves": {
            "Finishers": [
                "Running Lariat",
                "Short-Arm Lariat",
                "Spinning Lariat",
                "Ripcord Lariat",
                "Discus Lariat",
                "Jumping Lariat",
                "Rolling Lariat",
                "Corner Lariat",
                "Clothesline from Behind",
                "Pop-Up Lariat",
                "Swinging Lariat",
                "High-Impact Clothesline",
                "Rebound Lariat",
                "Avalanche Lariat",
                "Turning Clothesline",
                "Double-Handed Lariat",
                "Leaping Clothesline",
                "Snap Lariat",
                "Charging Clothesline",
                "Spinning Clothesline",
                "Running Arm Lariat",
                "Clothesline Takedown",
                "Short-Range Lariat",
                "Corner-to-Corner Lariat",
                "Explosive Lariat"
            ],
            "Signatures": [
                "Running Lariat",
                "Short-Arm Lariat",
                "Spinning Lariat",
                "Ripcord Lariat",
                "Discus Lariat",
                "Jumping Lariat",
                "Rolling Lariat",
                "Corner Lariat",
                "Clothesline from Behind",
                "Pop-Up Lariat",
                "Swinging Lariat",
                "High-Impact Clothesline",
                "Rebound Lariat",
                "Avalanche Lariat",
                "Turning Clothesline",
                "Double-Handed Lariat",
                "Leaping Clothesline",
                "Snap Lariat",
                "Charging Clothesline",
                "Spinning Clothesline",
                "Running Arm Lariat",
                "Clothesline Takedown",
                "Short-Range Lariat",
                "Corner-to-Corner Lariat",
                "Explosive Lariat"
            ]
        }
    }
}

# Default attribute values
DEFAULT_ATTRIBUTE_VALUE = 50
MIN_ATTRIBUTE_VALUE = 30
MAX_ATTRIBUTE_VALUE = 100

# Default starting attributes by archetype
def get_base_attributes(archetype, persona):
    """Generate base attributes for a wrestler based on archetype and persona"""
    attrs = {attr: DEFAULT_ATTRIBUTE_VALUE for attr in ATTRIBUTES}
    
    # Apply archetype bonuses
    if archetype == "Giant":
        attrs["Strength"] += 15
        attrs["Arm Power"] += 12
        attrs["Leg Power"] += 12
        attrs["Head Durability"] += 10
        attrs["Arm Durability"] += 10
        attrs["Leg Durability"] += 10
        attrs["Grapple Offense"] += 8
        attrs["Agility"] -= 15
        attrs["Movement Speed"] -= 10
        attrs["Aerial Offense"] -= 10
        
    elif archetype == "High Flyer":
        attrs["Aerial Offense"] += 15
        attrs["Aerial Range"] += 12
        attrs["Agility"] += 10
        attrs["Movement Speed"] += 10
        attrs["Aerial Reversal"] += 8
        attrs["Strength"] -= 10
        attrs["Head Durability"] -= 10
        attrs["Arm Durability"] -= 8
        attrs["Leg Durability"] -= 8
        
    elif archetype == "Technical":
        attrs["Technical Submission"] += 10
        attrs["Grapple Reversal"] += 8
        attrs["Strike Reversal"] += 8
        attrs["Aerial Reversal"] += 5
        attrs["Technical Submission Defense"] += 8
        attrs["Grapple Offense"] += 6
        attrs["Stamina"] += 5
        
    elif archetype == "Striker":
        attrs["Running Offense"] += 12
        attrs["Strike Reversal"] += 10
        attrs["Movement Speed"] += 8
        attrs["Stamina"] += 5
        attrs["Agility"] += 8
        attrs["Recovery"] += 5
        
    elif archetype == "Powerhouse":
        attrs["Strength"] += 12
        attrs["Arm Power"] += 10
        attrs["Leg Power"] += 10
        attrs["Grapple Offense"] += 10
        attrs["Stamina"] += 5
        attrs["Agility"] += 3
        attrs["Head Durability"] += 5
    
    # Apply persona bonuses
    if persona in PERSONAS:
        for attr, bonus in PERSONAS[persona]["bonus_attrs"].items():
            attrs[attr] += bonus
    
    # Ensure all values are within bounds
    for attr in attrs:
        attrs[attr] = max(MIN_ATTRIBUTE_VALUE, min(65, attrs[attr]))
    
    return attrs

# Shop prices
SHOP_PRICES = {
    "attribute_1": 150,      # +1 to any attribute
    "attribute_5": 700,      # +5 to any attribute
    "attribute_10": 1300,    # +10 to any attribute
}

# Currency settings defaults
DEFAULT_CURRENCY = {
    "name": "Dollars",
    "symbol": "$",
    "min_per_message": 5,
    "max_per_message": 15,
    "cooldown_seconds": 60
}

def feet_to_cm(feet):
    """Convert feet (decimal) to cm"""
    return int(feet * 30.48)

def get_height_for_archetype(archetype, gender):
    """Get height range in both feet and cm for an archetype and gender"""
    height_range = ARCHETYPES[archetype]["height_range"][gender]
    return {
        "feet_min": height_range[0],
        "feet_max": height_range[1],
        "cm_min": feet_to_cm(height_range[0]),
        "cm_max": feet_to_cm(height_range[1])
    }
