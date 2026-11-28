
const video = document.getElementById("webcam");
const cameraStatus = document.getElementById("camera-status");

const startButton = document.getElementById("start-camera");
const captureButton = document.getElementById("capture-btn");
const stopButton = document.getElementById("stop-camera");

let cameraStream = null;

// Start the webcam
async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
        cameraStatus.textContent =
            "Camera access requires localhost or HTTPS and a supported browser.";
        return;
    }

    startButton.disabled = true;
    cameraStatus.textContent = "Requesting camera permission...";

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
        });

        video.srcObject = cameraStream;
        await video.play();

        cameraStatus.textContent = "Camera is ready!";
        captureButton.disabled = false;
        stopButton.disabled = false;

    } catch (error) {
        stopCamera();

        if (error.name === "NotAllowedError") {
            cameraStatus.textContent =
                "Camera permission denied. Please allow camera access.";
        } else if (error.name === "NotFoundError") {
            cameraStatus.textContent =
                "No camera was found on this device.";
        } else {
            cameraStatus.textContent =
                "Unable to start camera. Please try again.";
        }

        console.error("Camera error:", error);
    }
}

// Stop the webcam and release the device
function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    video.srcObject = null;

    startButton.disabled = false;
    captureButton.disabled = true;
    stopButton.disabled = true;

    cameraStatus.textContent = "Camera stopped.";
}

// Connect buttons to functions
startButton.addEventListener("click", startCamera);
stopButton.addEventListener("click", stopCamera);

// Release camera when leaving the page
window.addEventListener("pagehide", stopCamera);


const canvas = document.getElementById("capture-canvas");
const capturedImage = document.getElementById("captured-image");

const MAX_IMAGE_SIZE = 1024 * 1024; // 1 MiB

let capturedImageBlob = null;
let capturedImageUrl = null;

// Capture a single webcam frame as JPEG
async function captureGesture() {
    if (!cameraStream || !video.videoWidth) {
        cameraStatus.textContent = "Start the camera first.";
        return;
    }

    captureButton.disabled = true;
    submitButton.disabled = true;
    capturedImageBlob = null;
    capturedImage.hidden = true;
    if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
        capturedImageUrl = null;
    }

    try {
        // Resize the image while preserving its proportions
        const scale = Math.min(1, 960 / video.videoWidth);

        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);

        const context = canvas.getContext("2d");
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        let imageBlob = null;

        // Compress the JPEG to stay below 1 MiB
        for (const quality of [0.85, 0.7, 0.5, 0.3]) {
            imageBlob = await new Promise(resolve => {
                canvas.toBlob(resolve, "image/jpeg", quality);
            });

            if (imageBlob && imageBlob.size <= MAX_IMAGE_SIZE) {
                break;
            }

            if (imageBlob && imageBlob.size > MAX_IMAGE_SIZE) {
                imageBlob = null;
            }
        }

        if (!imageBlob) {
            throw new Error("Image is too large. Please try again.");
        }

        // Save the image for later API submission
        capturedImageBlob = imageBlob;
        submitButton.disabled = false;

        capturedImageUrl = URL.createObjectURL(imageBlob);
        capturedImage.src = capturedImageUrl;
        capturedImage.hidden = false;

        cameraStatus.textContent =
            "Gesture captured successfully!";

        console.log("Captured JPEG size:", imageBlob.size, "bytes");

    } catch (error) {
        cameraStatus.textContent = error.message;
        console.error("Capture error:", error);

    } finally {
        captureButton.disabled = !cameraStream;
    }
}

captureButton.addEventListener("click", captureGesture);

const submitButton = document.getElementById("submit-gesture");

// Simulate the API until the Flask backend is ready
async function mockSubmitGesture(formData) {
    const image = formData.get("image");

    if (!(image instanceof Blob) || image.type !== "image/jpeg") {
        throw new Error("A valid JPEG image is required.");
    }

    if (image.size > MAX_IMAGE_SIZE) {
        throw new Error("Image exceeds the 1 MiB limit.");
    }

    // Simulated response, not a real server request
    return {
        id: `mock-${Date.now()}`,
        status: "pending"
    };
}

// Prepare and submit a captured gesture
async function submitGesture() {
    if (!capturedImageBlob) {
        cameraStatus.textContent = "Capture a gesture first.";
        return;
    }

    submitButton.disabled = true;
    cameraStatus.textContent = "Preparing gesture submission...";

    try {
        const formData = new FormData();

        formData.append(
            "image",
            capturedImageBlob,
            "gesture.jpg"
        );

        const response = await mockSubmitGesture(formData);

        console.log("Mock API response:", response);

        cameraStatus.textContent =
            "Mock submission successful! Ready for backend integration.";

    } catch (error) {
        cameraStatus.textContent = error.message;
        submitButton.disabled = false;
        console.error("Submission error:", error);
    }
}

submitButton.addEventListener("click", submitGesture);
