/* Module 2 -- render the Pusaka3D floor plan headless with the from-scratch
 * rasteriser.  node draw_plan.mjs --w 800 --h 600 [--plan pusaka_plan.json]
 *                                 [--fill] [--out out/plan_scratch.ppm] */
import { loadPlan, renderPlan, newFramebufferForPlan } from "./plan.mjs";
import { mkdirSync } from "node:fs";

const val = (k, d) => {
  const i = process.argv.indexOf(k);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith("--")
    ? process.argv[i + 1] : d;
};
const w = +val("--w", 800);
const h = +val("--h", 600);
const planPath = val("--plan", "pusaka_plan.json");
const out = val("--out", "out/plan_scratch.ppm");
const fill = process.argv.includes("--fill");

mkdirSync("out", { recursive: true });
const plan = loadPlan(planPath);
const fb = newFramebufferForPlan(plan, w, h);
const segs = renderPlan(fb, plan, { fillSilhouette: fill });
const n = fb.writePPM(out);
console.log(`plan "${plan.name}"`);
console.log(`polylines: ${plan.polylines.length}   segments: ${segs}   ` +
  `framebuffer: ${w}x${h}   ${fill ? "silhouette FILLED" : "outline only"}`);
console.log(`wrote ${out} (${n} bytes)`);
