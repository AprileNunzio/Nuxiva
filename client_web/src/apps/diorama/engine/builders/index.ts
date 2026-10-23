import * as THREE from 'three';
import type { Item, Recipe } from '../../types';
import { seeded } from '../rng';
import { learnedBuilder } from './learned';
import { canopy, footbridge, house, stationBuilding } from './buildings';
import { block, cylinder, grassPatch, path, petals, pond, road, rock } from './ground';
import type { BuildContext, Builder } from './kit';
import { bush, treeCherry, treeMaple, treePine } from './nature';
import { bench, car, fence, lamp, person, sign, vending } from './props';
import { crossing, platform, rails, train } from './rail';

const BUILDERS: Record<string, Builder> = {
  grass_patch: grassPatch, path, pond, rock, petals, road, block, cylinder, platform, rails, train, crossing, station_building: stationBuilding, canopy, footbridge,
  house, tree_cherry: treeCherry, tree_pine: treePine, tree_maple: treeMaple, bush, lamp, bench, fence, vending, sign, person, car,
};

export function buildItem(item: Item, ctx: BuildContext, recipes: Readonly<Record<string, Recipe>> = {}): THREE.Group {
  const holder = new THREE.Group();
  const recipe = recipes[item.kind];
  const build = BUILDERS[item.kind] ?? (recipe ? learnedBuilder(recipe) : undefined);
  if (build) holder.add(build(item.params, seeded(item.id), ctx));
  holder.position.set(item.x, item.y, item.z);
  holder.rotation.y = THREE.MathUtils.degToRad(item.rot);
  holder.scale.setScalar(item.scale);
  holder.userData.itemId = item.id;
  return holder;
}
