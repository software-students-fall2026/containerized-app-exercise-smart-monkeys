import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../static/camera.js", import.meta.url), "utf8");

for (const failure of ["drawing", "encoding"]) {
    test(`failed ${failure} cannot submit a previous capture`, async () => {
        const elements = {};
        const revoked = [];
        const context = vm.createContext({
            document: { getElementById: id => elements[id] ??= { addEventListener() {} } },
            window: { addEventListener() {} },
            console: { log() {}, error() {} },
            URL: { createObjectURL: () => "blob:preview", revokeObjectURL: url => revoked.push(url) }
        });
        vm.runInContext(source, context);
        vm.runInContext("cameraStream = {};", context);
        Object.assign(elements.webcam, { videoWidth: 640, videoHeight: 480 });
        const canvas = elements["capture-canvas"];
        let failed = false;
        canvas.getContext = () => ({ drawImage() {
            if (failed && failure === "drawing") throw new Error("Capture failed");
        } });
        canvas.toBlob = callback => callback(failed ? null : { size: 100 });
        await context.captureGesture();
        assert.equal(elements["submit-gesture"].disabled, false);
        assert.equal(elements["captured-image"].hidden, false);
        failed = true;
        await context.captureGesture();
        assert.equal(elements["submit-gesture"].disabled, true);
        assert.equal(elements["captured-image"].hidden, true);
        assert.deepEqual(revoked, ["blob:preview"]);
        await context.submitGesture();
        assert.equal(elements["camera-status"].textContent, "Capture a gesture first.");
        failed = false;
        await context.captureGesture();
        assert.equal(elements["submit-gesture"].disabled, false);
        assert.equal(elements["capture-btn"].disabled, false);
    });
}
