# forever-market digest

generated_at: 2026-11-14T11:30:02Z

Prices in gold (g). `-` = unknown. `region sale` is a 0-1 rate. `note` holds TSM updatedAt or the wago build.

## Sources

| source | fetched_at | rows | note |
|---|---|---|---|
| blizzard api | 2026-11-14 11:30:01 | 507889 | us, ruleset 1, 10 houses, 0 ids not in item |
| era_itemsparse | 2026-11-14 11:29:42 | 24442 | ItemSparse build 1.15.9.70576 |
| item | 2026-11-14 11:29:42 | 31986 | forever=19307 era=10184 missing=2495 |
| tsm_realm | 2026-11-14 11:29:43 | 6766 | 2026-11-14T07:17:51Z |
| tsm_region | 2026-11-14 11:29:45 | 7232 | 2026-11-13T08:38:44Z |
| wago_item | 2026-11-14 11:29:38 | 31986 | Item build 1.60.1.70790 |
| wago_itemsparse | 2026-11-14 11:29:40 | 19307 | ItemSparse build 1.60.1.70790 |

rows: 7

## Row counts

| table | rows |
|---|---|
| item | 31986 |
| price_realm | 6766 |
| price_region | 7232 |
| spell | 0 |
| spell_reagent | 0 |
| craft_output | 0 |
| trade | 0 |
| auction_life | 507889 |
| creature | 0 |
| area | 0 |
| drop | 0 |
| kill_event | 0 |
| loot_event | 0 |
| node_area | 0 |
| sync_log | 7 |
| loot_session | 0 |
| loot_source | 0 |
| loot_item_source | 0 |
| loot_item | 0 |
| api_house | 10 |
| api_auction | 274127 |
| api_commodity | 233762 |
| api_house_match | 0 |
| price_history | 32715 |
| index_history | 7 |
| api_fingerprint | 10 |
| sold_hour | 0 |

rows: 27

## SNAPSHOT

| metric | value |
|---|---|
| realm items with market value | 6765 |
| sum market value | 5,695,241.34g |
| median market value | 0.54g |
| items with market value >= 10g | 558 |
| realm items listed (minBO > 0) | 6133 |
| sum minBO, 1 unit each | 42,185.77g |

rows: 6

### Movers vs historical (market >= 1g)

| item | market | historical | change % |
|---|---|---|---|
| Recipe: Elixir of Strength | 246.26g | 1.01g | 24282.1% |
| Pattern: Cindercloth Cloak | 431.92g | 3.61g | 11864.4% |
| Pattern: Mooncloth Robe | 53.30g | 3.75g | 1319.5% |
| item 263937 | 9.03g | 1.09g | 728.8% |
| item 263935 | 3.73g | 0.55g | 579.0% |
| The Jackhammer | 165.73g | 25.00g | 562.9% |
| Pattern: Mooncloth Circlet | 63.86g | 10.26g | 522.4% |
| Flame Seared Signet | 20.64g | 4.00g | 415.9% |
| item 287031 | 48.95g | 10.89g | 349.5% |
| Red Dragonscale | 5.33g | 1.23g | 333.7% |

rows: 10

## GATHER

node value = market x classic yield (herb 1.5, ore 2.2, leather/cloth 1.0).

| item | type | market | minBO | region sale | node value |
|---|---|---|---|---|---|
| Death Lotus | Herb | 26.62g | 16.55g | 0.000 | 39.93g |
| Black Lotus | Herb | 23.28g | 14.00g | 0.217 | 34.92g |
| Refined Deeprock Salt | Leather | 34.30g | 23.68g | 0.157 | 34.30g |
| Mooncloth | Cloth | 27.92g | 25.00g | 0.080 | 27.92g |
| Guardian Stone | Ore/Stone | 12.57g | 2.95g | 0.062 | 27.65g |
| Cured Rugged Hide | Leather | 19.03g | 13.25g | 0.144 | 19.03g |
| Marefoil | Herb | 9.29g | 1.78g | 0.000 | 13.94g |
| Brilliant Chromatic Scale | Leather | 13.76g | 8.00g | 0.000 | 13.76g |
| Demonsage | Herb | 6.68g | 1.33g | 0.000 | 10.03g |
| Fel Hide | Leather | 6.57g | 2.50g | 0.166 | 6.57g |
| Red Dragonscale | Leather | 5.33g | 2.49g | 0.000 | 5.33g |
| Blue Dragonscale | Leather | 3.81g | 2.49g | 0.000 | 3.81g |
| Pitchblende | Ore/Stone | 1.48g | 0.42g | 0.339 | 3.25g |
| Black Dragonscale | Leather | 2.42g | 2.05g | 0.373 | 2.42g |
| Devilsaur Leather | Leather | 2.15g | 0.50g | 0.181 | 2.15g |
| Frostsaber Leather | Leather | 2.09g | 0.45g | 0.071 | 2.09g |
| Enchanted Leather | Leather | 2.05g | 1.20g | 0.252 | 2.05g |
| Stranglevine | Herb | 1.22g | 0.67g | 0.468 | 1.83g |
| Felcloth | Cloth | 1.71g | 0.34g | 0.332 | 1.71g |
| Plaguebloom | Herb | 1.02g | 0.34g | 0.234 | 1.54g |
| Pristine Scale | Leather | 1.53g | 0.75g | 0.347 | 1.53g |
| Heavy Thorium Ore | Ore/Stone | 0.67g | 0.23g | 0.044 | 1.47g |
| Icecap | Herb | 0.80g | 0.25g | 0.113 | 1.20g |
| Ghost Mushroom | Herb | 0.61g | 0.95g | 0.309 | 0.91g |
| Golden Sansam | Herb | 0.58g | 0.18g | 0.410 | 0.87g |
| Mountain Silversage | Herb | 0.55g | 0.21g | 0.190 | 0.82g |
| Dreamfoil | Herb | 0.52g | 0.23g | 0.463 | 0.79g |
| Heavy Scorpid Scale | Leather | 0.67g | 0.41g | 0.328 | 0.67g |
| Warbear Leather | Leather | 0.60g | 0.45g | 0.208 | 0.60g |
| Thorium Ore | Ore/Stone | 0.27g | 0.13g | 0.404 | 0.59g |
| Fel Leather | Leather | 0.58g | 0.17g | 0.000 | 0.58g |
| Rugged Hide | Leather | 0.57g | 0.05g | 0.192 | 0.57g |
| Bauxite | Ore/Stone | 0.26g | 0.04g | 0.541 | 0.56g |
| Scarce Herb Seeds | Herb | 0.36g | 0.39g | 0.217 | 0.53g |
| Light Silithid Carapace | Leather | 0.49g | 0.45g | 0.250 | 0.49g |
| Arthas' Tears | Herb | 0.32g | 0.19g | 0.330 | 0.48g |
| Gromsblood | Herb | 0.31g | 0.37g | 0.320 | 0.47g |
| Chimera Leather | Leather | 0.47g | 0.53g | 0.125 | 0.47g |
| Truesilver Ore | Ore/Stone | 0.21g | 0.12g | 0.503 | 0.45g |
| Dark Iron Ore | Ore/Stone | 0.20g | 0.15g | 0.309 | 0.45g |
| Rosecap | Herb | 0.26g | 0.11g | 0.610 | 0.39g |
| Red Whelp Scale | Leather | 0.34g | 0.20g | 0.346 | 0.34g |
| Ironweb Spider Silk | Cloth | 0.32g | 0.29g | 0.435 | 0.32g |
| Silithid Chitin | Leather | 0.32g | 0.31g | 0.060 | 0.32g |
| Frilled Lichen | Herb | 0.20g | 0.23g | 0.906 | 0.31g |
| Sungrass | Herb | 0.20g | 0.11g | 0.566 | 0.30g |
| Dense Stone | Ore/Stone | 0.13g | 0.06g | 0.601 | 0.28g |
| Wintersbite | Herb | 0.17g | 0.12g | 0.466 | 0.25g |
| Gold Ore | Ore/Stone | 0.11g | 0.09g | 0.711 | 0.24g |
| Blindweed | Herb | 0.16g | 0.09g | 0.404 | 0.23g |
| Unusual Herb Seeds | Herb | 0.15g | 0.07g | 0.194 | 0.22g |
| Firebloom | Herb | 0.15g | 0.18g | 0.537 | 0.22g |
| Mithril Ore | Ore/Stone | 0.10g | 0.08g | 0.774 | 0.21g |
| Thick Wolfhide | Leather | 0.18g | 0.10g | 0.114 | 0.18g |
| Purple Lotus | Herb | 0.11g | 0.06g | 0.522 | 0.17g |
| Cured Thick Hide | Leather | 0.17g | 0.13g | 0.357 | 0.17g |
| Cured Heavy Hide | Leather | 0.15g | 0.70g | 0.661 | 0.15g |
| Runecloth | Cloth | 0.14g | 0.06g | 0.670 | 0.14g |
| Silver Ore | Ore/Stone | 0.06g | 0.05g | 0.800 | 0.14g |
| Scorpid Scale | Leather | 0.14g | 0.13g | 0.647 | 0.14g |
| Black Whelp Scale | Leather | 0.13g | 0.05g | 0.332 | 0.13g |
| Grave Moss | Herb | 0.09g | 0.04g | 0.599 | 0.13g |
| Heavy Hide | Leather | 0.13g | 0.15g | 0.865 | 0.13g |
| Green Whelp Scale | Leather | 0.13g | 0.06g | 0.399 | 0.13g |
| Thick Hide | Leather | 0.13g | 0.06g | 0.435 | 0.13g |
| Rugged Leather | Leather | 0.12g | 0.16g | 0.738 | 0.12g |
| Fadeleaf | Herb | 0.08g | 0.05g | 0.714 | 0.12g |
| Turtle Scale | Leather | 0.12g | 0.20g | 0.715 | 0.12g |
| Goldthorn | Herb | 0.08g | 0.04g | 0.701 | 0.12g |
| Perfect Deviate Scale | Leather | 0.12g | 0.09g | 0.907 | 0.12g |
| Shadow Silk | Cloth | 0.11g | 0.16g | 0.386 | 0.11g |
| Coal | Ore/Stone | 0.05g | 0.05g | 0.700 | 0.10g |
| Swiftthistle | Herb | 0.07g | 0.07g | 0.850 | 0.10g |
| Heavy Stone | Ore/Stone | 0.04g | 0.03g | 0.927 | 0.10g |
| Spider's Silk | Cloth | 0.09g | 0.10g | 0.885 | 0.09g |
| Worn Dragonscale | Leather | 0.09g | 0.06g | 0.260 | 0.09g |
| Solid Stone | Ore/Stone | 0.04g | 0.01g | 0.765 | 0.09g |
| Thick Spider's Silk | Cloth | 0.08g | 0.07g | 0.604 | 0.08g |
| Pristine Hide | Leather | 0.07g | 0.03g | 0.535 | 0.07g |
| Iron Ore | Ore/Stone | 0.03g | 0.02g | 0.873 | 0.07g |
| Mageweave Cloth | Cloth | 0.06g | 0.05g | 0.901 | 0.06g |
| Liferoot | Herb | 0.04g | 0.02g | 0.698 | 0.06g |
| Khadgar's Whisker | Herb | 0.04g | 0.03g | 0.614 | 0.06g |
| Green Dragonscale | Leather | 0.06g | 0.05g | 0.106 | 0.06g |
| Thick Leather | Leather | 0.06g | 0.06g | 0.872 | 0.06g |
| Thick Murloc Scale | Leather | 0.05g | 0.05g | 0.268 | 0.05g |
| Shadowcat Hide | Leather | 0.05g | 0.03g | 0.184 | 0.05g |
| Cured Medium Hide | Leather | 0.05g | 0.04g | 0.757 | 0.05g |
| Pristine Leather | Leather | 0.05g | 0.05g | 0.799 | 0.05g |
| Ironfeather | Leather | 0.05g | 0.01g | 0.333 | 0.05g |
| Pyrite | Ore/Stone | 0.02g | 0.02g | 0.765 | 0.05g |
| Stranglekelp | Herb | 0.03g | 0.03g | 0.894 | 0.04g |
| Deeprock Salt | Leather | 0.04g | 0.03g | 0.432 | 0.04g |
| Uncommon Herb Seeds | Herb | 0.03g | 0.01g | 0.272 | 0.04g |
| Wildvine | Herb | 0.03g | 0.01g | 0.570 | 0.04g |
| Copper Ore | Ore/Stone | 0.02g | 0.01g | 0.935 | 0.04g |
| Medium Hide | Leather | 0.03g | 0.03g | 0.922 | 0.03g |
| Commonplace Herb Seeds | Herb | 0.02g | 0.01g | 0.415 | 0.03g |
| Long Tail Feather | Leather | 0.03g | 0.03g | 0.609 | 0.03g |
| Tin Ore | Ore/Stone | 0.01g | 0.01g | 0.904 | 0.03g |
| Jet Black Feather | Leather | 0.03g | 0.02g | 0.129 | 0.03g |
| Wild Steelbloom | Herb | 0.02g | 0.01g | 0.694 | 0.03g |
| Raptor Hide | Leather | 0.03g | 0.02g | 0.726 | 0.03g |
| Heavy Leather | Leather | 0.03g | 0.02g | 0.917 | 0.03g |
| Kingsblood | Herb | 0.02g | 0.01g | 0.826 | 0.02g |
| Silk Cloth | Cloth | 0.02g | 0.01g | 0.956 | 0.02g |
| Cured Light Hide | Leather | 0.02g | 0.02g | 0.789 | 0.02g |
| Briarthorn | Herb | 0.01g | 0.01g | 0.873 | 0.02g |
| Bruiseweed | Herb | 0.01g | 0.01g | 0.897 | 0.02g |
| Earthroot | Herb | 0.01g | 0.01g | 0.886 | 0.02g |
| Slimy Murloc Scale | Leather | 0.02g | 0.01g | 0.649 | 0.02g |
| Wool Cloth | Cloth | 0.01g | 0.01g | 0.959 | 0.01g |
| Coarse Stone | Ore/Stone | 0.01g | 0.00g | 0.903 | 0.01g |
| Light Hide | Leather | 0.01g | 0.01g | 0.908 | 0.01g |
| Medium Leather | Leather | 0.01g | 0.01g | 0.955 | 0.01g |
| Mageroyal | Herb | 0.01g | 0.01g | 0.894 | 0.01g |
| Peacebloom | Herb | 0.01g | 0.01g | 0.937 | 0.01g |
| Thin Kodo Leather | Leather | 0.01g | 0.60g | 0.257 | 0.01g |
| Salt | Leather | 0.01g | 0.01g | 0.502 | 0.01g |
| Light Leather | Leather | 0.00g | 0.01g | 0.960 | 0.00g |
| Deviate Scale | Leather | 0.00g | 0.00g | 0.701 | 0.00g |
| Silverleaf | Herb | 0.00g | 0.00g | 0.910 | 0.00g |
| Linen Cloth | Cloth | 0.00g | 0.00g | 0.950 | 0.00g |
| Rough Stone | Ore/Stone | 0.00g | 0.00g | 0.937 | 0.00g |
| Ruined Leather Scraps | Leather | 0.00g | 0.00g | 0.904 | 0.00g |
| Nexus Crystal | Enchanting | 77.61g | 49.00g | 0.000 | - |
| Delicate Arcanite Converter | Parts | 49.44g | 70.00g | 0.000 | - |
| Righteous Orb | Other | 22.44g | 11.55g | 0.222 | - |
| Fel Crystal | Other | 19.76g | 10.53g | 0.094 | - |
| Blood of the Mountain | Other | 19.72g | 9.35g | 0.285 | - |
| Arcane Crystal | Other | 17.54g | 17.00g | 0.405 | - |
| Torbernite | Other | 15.87g | 6.76g | 0.000 | - |
| Dark Rune | Other | 13.50g | 3.21g | 0.481 | - |
| Essence of Air | Elemental | 11.27g | 6.99g | 0.034 | - |
| Blue Sapphire | Other | 8.45g | 10.00g | 0.402 | - |
| Essence of Water | Elemental | 8.20g | 5.65g | 0.237 | - |
| Thick Logs | Other | 7.51g | - | 0.000 | - |
| Essence of Earth | Elemental | 7.31g | 4.16g | 0.538 | - |
| Azerothian Diamond | Other | 3.94g | 1.89g | 0.246 | - |
| Large Brilliant Shard | Enchanting | 3.47g | 2.56g | 0.436 | - |
| Truesilver Transformer | Parts | 3.21g | 3.48g | 0.000 | - |
| Golden Pearl | Other | 2.92g | 1.80g | 0.518 | - |
| Essence of Fire | Elemental | 2.76g | 3.55g | 0.363 | - |
| Viridian Dye | Other | 2.56g | 1.50g | 0.244 | - |
| Greater Eternal Essence | Enchanting | 2.46g | 1.70g | 0.185 | - |
| Thorium Tube | Parts | 2.41g | 1.14g | 0.302 | - |
| Small Brilliant Shard | Enchanting | 2.39g | 1.20g | 0.146 | - |
| Large Radiant Shard | Enchanting | 2.28g | 2.02g | 0.220 | - |
| Powerful Mojo | Other | 1.92g | 4.75g | 0.183 | - |
| Globe of Water | Elemental | 1.90g | 0.44g | 0.626 | - |
| Huge Emerald | Other | 1.87g | 2.00g | 0.253 | - |
| Essence of Undeath | Elemental | 1.79g | 0.44g | 0.183 | - |
| Ghost Dye | Other | 1.58g | 0.45g | 0.054 | - |
| Large Opal | Other | 1.58g | 0.71g | 0.244 | - |
| SAF-T Casing | Parts | 1.38g | 4.16g | 0.000 | - |
| Thorium Widget | Parts | 1.13g | 0.48g | 0.000 | - |
| Small Radiant Shard | Enchanting | 1.13g | 0.98g | 0.260 | - |
| Greater Nether Essence | Enchanting | 1.06g | 1.16g | 0.358 | - |
| Inlaid Mithril Cylinder | Parts | 0.98g | 2.00g | 0.209 | - |
| Illusion Dust | Enchanting | 0.95g | 0.48g | 0.229 | - |
| No Slip SAF-T Padding | Parts | 0.94g | 1.00g | 0.000 | - |
| Lesser Eternal Essence | Enchanting | 0.92g | 0.64g | 0.196 | - |
| Larval Acid | Other | 0.86g | 0.59g | 0.128 | - |
| Long Elegant Feather | Other | 0.74g | 0.50g | 0.701 | - |
| Surgical Tourniquet | Other | 0.72g | 0.50g | 0.000 | - |
| Star Ruby | Other | 0.70g | 0.54g | 0.550 | - |
| EZ-Thro Fireproof Fuse | Parts | 0.69g | 0.05g | 0.240 | - |
| Living Essence | Elemental | 0.66g | 0.35g | 0.401 | - |
| SAF-T Tabs | Parts | 0.62g | 0.65g | 0.000 | - |
| Sandworm Meat | Meat | 0.60g | 0.25g | 0.043 | - |
| Black Pearl | Other | 0.57g | 0.13g | 0.593 | - |
| Lesser Mana Oil | Enchanting | 0.55g | 0.18g | 0.160 | - |
| Magenta Dye | Other | 0.54g | 0.23g | 0.457 | - |
| Large Glowing Shard | Enchanting | 0.49g | 0.34g | 0.607 | - |
| Star Wood | Other | 0.47g | 0.40g | 0.371 | - |
| Gyromatic Micro-Adjustor | Parts | 0.46g | 0.23g | 0.365 | - |
| Cerulean Dye | Other | 0.45g | 0.50g | 0.725 | - |
| Imbued Vial | Other | 0.44g | 0.21g | 0.000 | - |
| Heart of Fire | Elemental | 0.39g | 0.15g | 0.502 | - |
| Lesser Nether Essence | Enchanting | 0.37g | 0.33g | 0.292 | - |
| Large Glimmering Shard | Enchanting | 0.36g | 0.45g | 0.713 | - |
| Elemental Fire | Elemental | 0.36g | 0.23g | 0.636 | - |
| Mithril Casing | Parts | 0.33g | 0.20g | 0.291 | - |
| Goblin Rocket Fuel | Parts | 0.32g | 0.15g | 0.129 | - |
| Giant Egg | Meat | 0.32g | 0.12g | 0.757 | - |
| Breath of Wind | Elemental | 0.32g | 0.56g | 0.110 | - |
| Greater Mystic Essence | Enchanting | 0.32g | 0.22g | 0.624 | - |
| Engineer's Ink | Parts | 0.32g | 0.25g | 0.000 | - |
| Blue Pearl | Other | 0.31g | 0.14g | 0.641 | - |
| Pink Dye | Other | 0.29g | 0.22g | 0.010 | - |
| Dream Dust | Enchanting | 0.28g | 0.34g | 0.359 | - |
| Elemental Air | Elemental | 0.28g | 0.13g | 0.559 | - |
| Purple Dye | Other | 0.27g | 0.16g | 0.047 | - |
| Unstable Trigger | Parts | 0.26g | 0.21g | 0.308 | - |
| Mithril Tube | Parts | 0.26g | 0.20g | 0.294 | - |
| Sandpaper | Parts | 0.25g | 0.14g | 0.322 | - |
| Aquamarine | Other | 0.24g | 0.12g | 0.284 | - |
| Elemental Earth | Elemental | 0.23g | 0.16g | 0.682 | - |
| Strong Flux | Other | 0.22g | 0.22g | 0.591 | - |
| Heavy Stock | Parts | 0.22g | 0.19g | 0.194 | - |
| Iridescent Pearl | Other | 0.21g | 0.08g | 0.833 | - |
| Small Flame Sac | Other | 0.20g | 0.18g | 0.699 | - |
| Black Vitriol | Other | 0.20g | 0.54g | 0.267 | - |
| Swollen Venom Sac | Other | 0.19g | 0.10g | 0.338 | - |
| Fused Wiring | Parts | 0.19g | 0.12g | 0.523 | - |
| Tough Condor Meat | Meat | 0.18g | 0.45g | 0.819 | - |
| Heart of the Wild | Elemental | 0.18g | 0.05g | 0.438 | - |
| Seasonal Fish Steaks | Meat | 0.18g | 0.16g | 0.000 | - |
| Core of Earth | Elemental | 0.18g | 0.10g | 0.268 | - |
| Heavy Kodo Meat | Meat | 0.17g | 0.10g | 0.346 | - |
| Ichor of Undeath | Elemental | 0.17g | 0.07g | 0.171 | - |
| Greater Astral Essence | Enchanting | 0.17g | 0.15g | 0.617 | - |
| Huge Venom Sac | Other | 0.17g | 0.20g | 0.190 | - |
| Small Glowing Shard | Enchanting | 0.17g | 0.10g | 0.516 | - |
| Coyote Meat | Meat | 0.17g | 0.13g | 0.736 | - |
| Flask of Big Mojo | Other | 0.16g | 0.05g | 0.286 | - |
| Lesser Wizard Oil | Enchanting | 0.16g | 0.12g | 0.470 | - |
| Orange Dye | Other | 0.15g | 0.08g | 0.051 | - |
| Citrine | Other | 0.15g | 0.15g | 0.770 | - |
| Tender Crab Meat | Meat | 0.14g | 0.06g | 0.813 | - |
| Superior Poultice | Other | 0.14g | 0.08g | 0.113 | - |
| Raw Whitescale Salmon | Meat | 0.13g | 0.15g | 0.123 | - |
| Elemental Water | Elemental | 0.13g | 0.09g | 0.724 | - |
| Black Dye | Other | 0.12g | 0.12g | 0.229 | - |
| Lesser Mystic Essence | Enchanting | 0.12g | 0.07g | 0.422 | - |
| Gyrochronatom | Parts | 0.11g | 0.08g | 0.381 | - |
| Vision Dust | Enchanting | 0.11g | 0.10g | 0.598 | - |
| Dense Blasting Powder | Parts | 0.11g | 0.11g | 0.630 | - |
| Iron Strut | Parts | 0.11g | 0.08g | 0.588 | - |
| Blank Parchment | Other | 0.11g | 0.04g | 0.052 | - |
| EZ-Thro Wrap | Parts | 0.11g | 0.10g | 0.505 | - |
| Whimsyfin | Other | 0.09g | 0.07g | 0.372 | - |
| Bronze Framework | Parts | 0.09g | 0.07g | 0.497 | - |
| Darkclaw Lobster | Meat | 0.08g | 0.06g | 0.622 | - |
| Stonescale Oil | Other | 0.08g | 0.05g | 0.210 | - |
| Chef's Knife | Other | 0.08g | 0.01g | 0.050 | - |
| Jade | Other | 0.07g | 0.07g | 0.687 | - |
| Giant Clam Meat | Meat | 0.07g | 0.03g | 0.421 | - |
| Turtle Meat | Meat | 0.07g | 0.02g | 0.777 | - |
| Potent Anti-Venom | Other | 0.07g | 0.02g | 0.272 | - |
| Moss Agate | Other | 0.07g | 0.07g | 0.887 | - |
| Solid Blasting Powder | Parts | 0.07g | 0.04g | 0.286 | - |
| Copper Modulator | Parts | 0.07g | 0.07g | 0.781 | - |
| Lesser Moonstone | Other | 0.06g | 0.06g | 0.757 | - |
| Raw Spinefin Halibut | Meat | 0.06g | 0.02g | 0.021 | - |
| Crag Boar Rib | Meat | 0.06g | 0.04g | 0.578 | - |
| Raw Nightfin Snapper | Meat | 0.06g | 0.04g | 0.224 | - |
| Wicked Claw | Other | 0.06g | 0.05g | 0.455 | - |
| Tiger Meat | Meat | 0.06g | 0.06g | 0.854 | - |
| Goretusk Snout | Meat | 0.06g | 0.03g | 0.597 | - |
| Whirring Bronze Gizmo | Parts | 0.05g | 0.04g | 0.538 | - |
| Lesser Astral Essence | Enchanting | 0.05g | 0.05g | 0.480 | - |
| Raw Sunscale Salmon | Meat | 0.05g | 0.04g | 0.421 | - |
| Soft Frenzy Flesh | Meat | 0.05g | 0.01g | 0.178 | - |
| Crystal Vial | Other | 0.05g | 0.05g | 0.407 | - |
| Crawler Meat | Meat | 0.05g | 0.04g | 0.846 | - |
| Sulfuric Acid | Other | 0.05g | 0.05g | 0.504 | - |
| Gold Power Core | Parts | 0.05g | 0.04g | 0.337 | - |
| Heavy Blasting Powder | Parts | 0.05g | 0.04g | 0.781 | - |
| Tender Wolf Meat | Meat | 0.05g | 0.04g | 0.666 | - |
| Soul Dust | Enchanting | 0.05g | 0.05g | 0.700 | - |
| Bronze Tube | Parts | 0.05g | 0.06g | 0.738 | - |
| Blackmouth Oil | Other | 0.05g | 0.05g | 0.527 | - |
| Red Wolf Meat | Meat | 0.04g | 0.03g | 0.825 | - |
| Buzzard Wing | Meat | 0.04g | 0.02g | 0.708 | - |
| Boar Ribs | Meat | 0.04g | 0.02g | 0.876 | - |
| Gray Dye | Other | 0.04g | 0.04g | 0.498 | - |
| Copper Tube | Parts | 0.04g | 0.04g | 0.707 | - |
| Small Glimmering Shard | Enchanting | 0.04g | 0.04g | 0.790 | - |
| Wooden Stock | Parts | 0.04g | 0.03g | 0.192 | - |
| Yellow Dye | Other | 0.04g | 0.04g | 0.101 | - |
| Hexed Pendant | Enchanting | 0.04g | 0.07g | 0.202 | - |
| Flask of Mojo | Other | 0.04g | 0.03g | 0.387 | - |
| Small Lustrous Pearl | Other | 0.03g | 0.02g | 0.871 | - |
| Raw Glossy Mightfish | Meat | 0.03g | 0.04g | 0.519 | - |
| Greater Magic Essence | Enchanting | 0.03g | 0.03g | 0.800 | - |
| Leather Tourniquet | Other | 0.03g | 0.05g | 0.032 | - |
| Shadowgem | Other | 0.03g | 0.03g | 0.912 | - |
| White Spider Meat | Meat | 0.03g | 0.02g | 0.696 | - |
| Small Egg | Meat | 0.03g | 0.02g | 0.780 | - |
| Raw Greater Sagefish | Meat | 0.03g | 0.01g | 0.571 | - |
| Raptor Flesh | Meat | 0.02g | 0.01g | 0.895 | - |
| Large Venom Sac | Other | 0.02g | 0.02g | 0.558 | - |
| Large Fang | Other | 0.02g | 0.02g | 0.657 | - |
| Mystery Meat | Meat | 0.02g | 0.01g | 0.904 | - |
| Simple Flour | Meat | 0.02g | 0.02g | 0.103 | - |
| Stonescale Eel | Other | 0.02g | 0.02g | 0.710 | - |
| Raw Loch Frenzy | Meat | 0.02g | 0.03g | 0.243 | - |
| Handful of Copper Bolts | Parts | 0.02g | 0.04g | 0.731 | - |
| Murloc Eye | Meat | 0.02g | 0.02g | 0.683 | - |
| Soothing Spices | Other | 0.02g | 0.02g | 0.367 | - |
| Naga Scale | Other | 0.02g | 0.01g | 0.162 | - |
| Oily Blackmouth | Other | 0.02g | 0.02g | 0.915 | - |
| Thunder Lizard Tail | Meat | 0.02g | 0.02g | 0.891 | - |
| Zesty Clam Meat | Meat | 0.02g | 0.04g | 0.578 | - |
| Stringy Wolf Meat | Meat | 0.02g | 0.02g | 0.940 | - |
| Chunk of Boar Meat | Meat | 0.02g | 0.02g | 0.833 | - |
| Iron Buckle | Parts | 0.02g | 0.01g | 0.400 | - |
| Clam Meat | Meat | 0.02g | 0.02g | 0.918 | - |
| Lightning Eel | Other | 0.02g | 0.00g | 0.096 | - |
| Stag Meat | Meat | 0.02g | 0.02g | 0.754 | - |
| Woolen Tourniquet | Other | 0.02g | 0.02g | 0.036 | - |
| Green Dye | Other | 0.02g | 0.01g | 0.349 | - |
| Lion Meat | Meat | 0.01g | 0.01g | 0.846 | - |
| Lean Wolf Flank | Meat | 0.01g | 0.00g | 0.772 | - |
| Weak Flux | Other | 0.01g | 0.01g | 0.395 | - |
| Raw Mithril Head Trout | Meat | 0.01g | 0.01g | 0.705 | - |
| Tigerseye | Other | 0.01g | 0.01g | 0.894 | - |
| Raptor Egg | Meat | 0.01g | 0.01g | 0.871 | - |
| Small Venom Sac | Other | 0.01g | 0.01g | 0.728 | - |
| Lesser Magic Essence | Enchanting | 0.01g | 0.01g | 0.777 | - |
| Flint and Tinder | Other | 0.01g | 0.01g | 0.558 | - |
| Blue Dye | Other | 0.01g | 0.01g | 0.224 | - |
| Meaty Bat Wing | Meat | 0.01g | 0.01g | 0.871 | - |
| Fire Oil | Other | 0.01g | 0.00g | 0.418 | - |
| Firefin Snapper | Other | 0.01g | 0.01g | 0.746 | - |
| Raw Brilliant Smallfish | Meat | 0.01g | 0.01g | 0.929 | - |
| Tender Crocolisk Meat | Meat | 0.01g | 0.01g | 0.756 | - |
| Big Bear Meat | Meat | 0.01g | 0.01g | 0.853 | - |
| Strange Dust | Enchanting | 0.01g | 0.01g | 0.891 | - |
| Goretusk Liver | Meat | 0.01g | 0.01g | 0.680 | - |
| Red Dye | Other | 0.01g | 0.01g | 0.338 | - |
| Tangy Clam Meat | Meat | 0.01g | 0.00g | 0.867 | - |
| Flask of Oil | Parts | 0.01g | 0.02g | 0.409 | - |
| Fist-sized Spinneret | Other | 0.01g | 0.01g | 0.000 | - |
| Stringy Vulture Meat | Meat | 0.01g | 0.00g | 0.532 | - |
| Raw Sagefish | Meat | 0.01g | 0.00g | 0.805 | - |
| Coarse Blasting Powder | Parts | 0.01g | 0.00g | 0.740 | - |
| Hot Spices | Other | 0.01g | 0.01g | 0.548 | - |
| Murloc Fin | Meat | 0.01g | 0.00g | 0.730 | - |
| Raw Spotted Yellowtail | Meat | 0.01g | 0.00g | 0.676 | - |
| Raw Slitherskin Mackerel | Meat | 0.01g | 0.00g | 0.868 | - |
| Leaded Vial | Other | 0.01g | 0.01g | 0.400 | - |
| Simple Wood | Other | 0.01g | 0.01g | 0.679 | - |
| Bleach | Other | 0.01g | 0.00g | 0.139 | - |
| Crisp Spider Meat | Meat | 0.01g | 0.00g | 0.308 | - |
| Sharp Claw | Other | 0.01g | 0.01g | 0.757 | - |
| Bear Meat | Meat | 0.00g | 0.00g | 0.780 | - |
| Scorpid Stinger | Meat | 0.00g | 0.01g | 0.772 | - |
| Crocolisk Meat | Meat | 0.00g | 0.00g | 0.540 | - |
| Kodo Meat | Meat | 0.00g | 0.00g | 0.527 | - |
| Simple Poultice | Other | 0.00g | 0.00g | 0.136 | - |
| Raw Bristle Whisker Catfish | Meat | 0.00g | 0.00g | 0.890 | - |
| Raw Redgill | Meat | 0.00g | 0.00g | 0.243 | - |
| Silver Contact | Parts | 0.00g | 0.00g | 0.367 | - |
| Raw Rainbow Fin Albacore | Meat | 0.00g | 0.00g | 0.773 | - |
| Golem Isospring | Parts | 0.00g | 0.00g | 0.673 | - |
| Strider Meat | Meat | 0.00g | 0.00g | 0.827 | - |
| Gooey Spider Leg | Meat | 0.00g | 0.00g | 0.695 | - |
| Luminous Residue | Enchanting | 0.00g | 0.00g | 0.219 | - |
| Crawler Claw | Meat | 0.00g | 0.00g | 0.769 | - |
| Boar Intestines | Meat | 0.00g | 0.00g | 0.463 | - |
| Malachite | Other | 0.00g | 0.00g | 0.615 | - |
| Rough Blasting Powder | Parts | 0.00g | 0.00g | 0.825 | - |
| Spider Ichor | Meat | 0.00g | 0.00g | 0.762 | - |
| Raw Rockscale Cod | Meat | 0.00g | 0.00g | 0.503 | - |
| Raw Longjaw Mud Snapper | Meat | 0.00g | 0.00g | 0.827 | - |
| Mote of Magic | Enchanting | 0.00g | 0.00g | 0.458 | - |
| Empty Vial | Other | 0.00g | 0.00g | 0.701 | - |
| Mild Spices | Other | 0.00g | 0.00g | 0.483 | - |
| Small Spider Leg | Meat | 0.00g | 0.00g | 0.586 | - |

rows: 361

## KILL

no loot data yet

rows: 0

## FARM

pace: - (no FARM rows)

sources with kills >= 10 from the KILL table, by total/kill, cap 25. best item = largest share of loot value; loot share = percent of the source's loot value from it; rate = its drops/kills in percent. confidence: ok at kills >= 50, thin at 10-49.

| source | kills | total/kill | loot share | best item | rate | confidence |
|---|---|---|---|---|---|---|

rows: 0

sources considered: 0, dropped for low sample (kills < 10): 0, unlabelled excluded: 0
value source: buyout 0%, vendor 0%, quest 0%, none 0% (0 drops)

## BOE

bind on equip, quality >= 2, seen dropping in your own loot log; value = max(0.95 x buyout, vendor), kept when value > vendor or value >= 50s. buyout = realm minBO. premium = value / vendor. flag: scarce = no listing and value >= 2g; demand = region sale rate >= 0.25; thin = listed, sale rate missing or < 0.05; vendor = otherwise. Top 20 by value.

| item | ilvl | q | vendor | buyout | value | premium | listings | sale rate | flag |
|---|---|---|---|---|---|---|---|---|---|

rows: 0

candidates: 0, dropped for value source none: 0

flags are price-and-liquidity signals, not proof of buyer interest

## CRAFT

cost = sum(qty x mat price) / items per craft, realm price first; `*` after profession = some mat priced from region. sell = 0.95 x realm market. margin % = 100 x profit / cost. HIDDEN = profit > 0 and nothing listed. sale rate is region, 0-1. Top 30 by profit.

| item | profession | skill | cost | sell | profit | margin % | listed | sale rate |
|---|---|---|---|---|---|---|---|---|

rows: 0

skipped: 0 outputs with unpriced materials, 0 with no realm market value (see WATCH); 0 outputs fully priced.

## FLIP

realm items, market >= 1g, minBO <= 0.7 x market; top 25 by gap.

| item | market | minBO | gap | gap % |
|---|---|---|---|---|
| Nostro's Compendium of Dragon Slaying | 5,634,491.16g | 475.00g | 5,634,016.16g | 100.0% |
| Papal Fez | 3,396.15g | 250.00g | 3,146.15g | 92.6% |
| Recipe: Flask of Petrification | 638.96g | 150.51g | 488.45g | 76.4% |
| Recipe: Flask of the Titans | 1,059.04g | 600.78g | 458.27g | 43.3% |
| Cloudkeeper Legplates | 1,444.39g | 1,000.00g | 444.39g | 30.8% |
| Lifestone | 351.49g | 45.00g | 306.49g | 87.2% |
| Recipe: Transmute Undeath to Water | 521.42g | 225.70g | 295.72g | 56.7% |
| A Thoroughly Read Copy of "Nat Pagle's Extreme' Anglin." | 537.09g | 250.00g | 287.09g | 53.5% |
| Recipe: Flask of Distilled Wisdom | 430.38g | 149.21g | 281.17g | 65.3% |
| Elemental Mage Staff | 438.86g | 200.00g | 238.86g | 54.4% |
| Myrmidon's Signet | 352.96g | 120.00g | 232.96g | 66.0% |
| Formula: Enchant Weapon - Crusader | 432.82g | 210.00g | 222.82g | 51.5% |
| Shadowblade | 278.84g | 65.00g | 213.84g | 76.7% |
| Totem of the Storm | 281.42g | 80.00g | 201.42g | 71.6% |
| Parrot Cage (Hyacinth Macaw) | 233.63g | 36.39g | 197.24g | 84.4% |
| Jeweled Amulet of Cainwyn | 283.55g | 100.00g | 183.55g | 64.7% |
| Axe of the Deep Woods | 329.38g | 149.98g | 179.40g | 54.5% |
| Pattern: Truefaith Vestments | 238.39g | 59.98g | 178.41g | 74.8% |
| Orb of Deception | 210.10g | 38.98g | 171.12g | 81.4% |
| Recipe: Elixir of Strength | 246.26g | 80.00g | 166.26g | 67.5% |
| Krol Blade | 362.64g | 200.00g | 162.64g | 44.8% |
| Recipe: Greater Fire Protection Potion | 196.74g | 36.00g | 160.74g | 81.7% |
| Blueprint: Iron Oven | 347.27g | 200.00g | 147.27g | 42.4% |
| Pattern: Big Bag of Enchantment | 196.36g | 55.00g | 141.36g | 72.0% |
| Dwarven Hand Cannon | 230.13g | 99.00g | 131.13g | 57.0% |

rows: 25

## API

official Blizzard API, house 113 (Horde Auction House, ruleset 1, chosen by most auctions). api minBO = min(buyout / quantity) per unit, api qty = sum(quantity), api listings = auction rows; tsm market = local realm market value; diff % = 100 x (api minBO - tsm market) / tsm market. Top 20 by api minBO.

| item | api minBO | api qty | api listings | tsm market | diff % |
|---|---|---|---|---|---|
| Plans: Lionheart Helm | 3,999.26g | 2 | 2 | 4,700.17g | -14.9% |
| Pattern: Timbermaw Tunic | 2,000.13g | 1 | 1 | - | - |
| Blueprint: Arcane Forge | 1,500.00g | 1 | 1 | 5,000.01g | -70.0% |
| Skullflame Shield | 1,250.35g | 2 | 2 | 1,214.97g | 2.9% |
| Alcor's Sunrazor | 1,000.00g | 1 | 1 | 355.27g | 181.5% |
| Cloudkeeper Legplates | 1,000.00g | 1 | 1 | 1,444.39g | -30.8% |
| Beasts Deck | 900.01g | 1 | 1 | 400.01g | 125.0% |
| item 284587 | 888.89g | 1 | 1 | 900.00g | -1.2% |
| Pattern: Gloves of Spell Mastery | 800.26g | 1 | 1 | - | - |
| Pattern: Warbear Helm | 750.13g | 2 | 2 | 269.90g | 177.9% |
| Pattern: Invulnerable Mail | 650.01g | 2 | 2 | 625.01g | 4.0% |
| Recipe: Flask of the Titans | 600.78g | 4 | 4 | 1,059.04g | -43.3% |
| Sash of Mercy | 600.00g | 1 | 1 | 600.00g | 0.0% |
| Recipe: Greater Shadow Protection Potion | 500.91g | 1 | 1 | 315.67g | 58.7% |
| Recipe: Flask of Supreme Power | 500.51g | 1 | 1 | 139.51g | 258.8% |
| Sword of Zeal | 500.32g | 1 | 1 | 335.01g | 49.3% |
| Fel Tainted Journal | 500.01g | 2 | 2 | - | - |
| Papal Fez | 500.00g | 1 | 1 | 3,396.15g | -85.3% |
| Plans: Masterwork Stormhammer | 500.00g | 1 | 1 | - | - |
| Brain Hacker | 499.99g | 4 | 4 | 473.27g | 5.6% |

rows: 20

auctions read: 111032; unresolved ids: 0; single house only: the five Horde houses are separate markets and are never summed

## SOLD

api sold = auctions that vanished while their remaining duration could not have expired, so cancellations and real sales both count here; tsm rate is the modelled sale rate. my sales come from your own TSM Accounting log.

| item | api sold | api qty | api avg unit | tsm rate | tsm sold/day | my sales | my avg unit |
|---|---|---|---|---|---|---|---|

rows: 0


auctions tracked: 507889, gone: 0, inferred sold: 0
your trades: 0 sales worth -, 0 buys costing -
## WATCH

recipe outputs or drops with no realm price; showing 0 of 0.

| item | reason |
|---|---|

rows: 0
