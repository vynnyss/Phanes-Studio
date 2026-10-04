// Official meshoptimizer WASM simplifier; all paths come from the local worker.
const fs = require("node:fs");
const path = require("node:path");
const { MeshoptSimplifier } = require("../runtime/tools/meshoptimizer/meshopt_simplifier.js");

async function main() {
    const [inputPath, outputPath, targetText, mode, errorText] = process.argv.slice(2);
    const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
    const positions = new Float32Array(input.positions);
    const indices = new Uint32Array(input.indices);
    const normals = new Float32Array(input.normals);
    const target = Number(targetText) * 3;
    const errorLimit = Number(errorText);
    let result;
    let error;
    await MeshoptSimplifier.ready;
    const started = performance.now();
    if (mode === "position") {
        [result, error] = MeshoptSimplifier.simplify(
            indices, positions, 3, target, errorLimit, ["LockBorder"]
        );
    } else {
        const weights = mode === "normal-update" ? [.1, .1, .1] : [0, 0, 0];
        const [count, measuredError] = MeshoptSimplifier.simplifyWithUpdate(
            indices, positions, 3, normals, 3, weights, null,
            target, errorLimit, ["LockBorder"]
        );
        result = indices.slice(0, count);
        error = measuredError;
    }
    fs.writeFileSync(outputPath, JSON.stringify({
        positions: Array.from(positions),
        indices: Array.from(result),
        error, errorLimit, mode,
        seconds: (performance.now() - started) / 1000,
        version: "1.3", flags: ["LockBorder"],
        triangles: result.length / 3,
    }));
}
main().catch(error => {
    process.stderr.write(String(error.stack || error));
    process.exitCode = 1;
});
