// Debounce function
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}

// Update slice display
const updateSlices = debounce(function() {
    $('.loading').show();
    
    const sliceX = $('#slice-x').val();
    const sliceY = $('#slice-y').val();
    const sliceZ = $('#slice-z').val();
    
    $.ajax({
        url: '/update_slice',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            filename: filename,
            slice_x: sliceX,
            slice_y: sliceY,
            slice_z: sliceZ
        }),
        success: function(response) {
            // Update images - 只更新轴状面和矢状面视图
            // 轴状面视图 (axial)
            const axialImgPath = '/static/images/' + response.images[0] + '?t=' + new Date().getTime();
            $('#image-0').attr('src', axialImgPath);
            $('#slice-info-0').text(response.slice_indices[0]);
            
            // 矢状面视图 (sagittal)
            const sagittalImgPath = '/static/images/' + response.images[2] + '?t=' + new Date().getTime();
            $('#image-1').attr('src', sagittalImgPath);
            $('#slice-info-1').text(response.slice_indices[2]);
            
            // 更新单独的矢状面视图
            $('#sagittal-image').attr('src', sagittalImgPath);
            $('#sagittal-slice-info').text(response.slice_indices[2]);
            
            $('.loading').hide();
        },
        error: function() {
            alert('Failed to update slices');
            $('.loading').hide();
        }
    });
}, 100);

// Listen for slider changes
$('#slice-x').on('input', function() {
    $('#slice-x-value').text($(this).val());
    updateSlices();
});

$('#slice-y').on('input', function() {
    $('#slice-y-value').text($(this).val());
    updateSlices();
});

$('#slice-z').on('input', function() {
    $('#slice-z-value').text($(this).val());
    updateSlices();
});

// Add prompt submission functionality
$('#submit-prompt').on('click', function() {
    const promptText = $('#prompt-text').val();
    if (!promptText.trim()) {
        alert('Please enter prompt content');
        return;
    }
    
    const sliceX = $('#slice-x').val();
    const sliceY = $('#slice-y').val();
    const sliceZ = $('#slice-z').val();
    
    $.ajax({
        url: '/process_prompt',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            filename: filename,
            prompt: promptText,
            slice_x: sliceX,
            slice_y: sliceY,
            slice_z: sliceZ
        }),
        success: function(response) {
            $('#prompt-result').html('<p>' + response.result + '</p>');
        },
        error: function() {
            alert('Failed to process prompt');
        }
    });
});

let audioBlob = null;
let mediaRecorder;
let audioChunks = [];

$('#record-btn').on('click', function() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();
            audioChunks = [];
            mediaRecorder.ondataavailable = e => {
                audioChunks.push(e.data);
            };
            mediaRecorder.onstop = e => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(audioBlob);
                $('#audio-playback').attr('src', audioUrl).show();

                // Upload audio to backend
                const formData = new FormData();
                formData.append('audio', audioBlob, 'record.wav');
                formData.append('filename', filename);
                $.ajax({
                    url: '/upload_audio',
                    type: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function(response) {
                        alert('Audio upload successful');
                    },
                    error: function() {
                        alert('Audio upload failed');
                    }
                });
            };
            $('#record-btn').attr('disabled', true);
            $('#stop-btn').attr('disabled', false);
        })
        .catch(err => {
            alert('Cannot access microphone: ' + err);
        });
});

$('#stop-btn').on('click', function() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        $('#record-btn').attr('disabled', false);
        $('#stop-btn').attr('disabled', true);
        $('#transcribe-btn').prop('disabled', false); // Enable transcription after recording ends
    }
});

// Transcribe button event
$('#transcribe-btn').on('click', function() {
    $('#transcribe-btn').prop('disabled', true);
    $('#transcript-result').text('Transcribing...');
    $.ajax({
        url: '/transcribe_audio',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ filename: filename }),
        success: function(response) {
            if (response.success) {
                $('#transcript-result').text('Transcription result: ' + response.transcript);
            } else {
                $('#transcript-result').text('Transcription failed: ' + (response.error || 'Unknown error'));
            }
        },
        error: function() {
            $('#transcript-result').text('Transcription request failed');
        }
    });
});

// Get filename
const filename = document.querySelector('h2').textContent.replace('File: ', '');
const currentFilename = filename;

// Sagittal view zoom functionality
$(document).ready(function() {
    const sagittalImage = document.getElementById('sagittal-image');
    let scale = 1;
    let isDragging = false;
    let startX, startY, translateX = 0, translateY = 0;
    
    // Zoom functionality
    $('#zoom-in').on('click', function() {
        scale *= 1.2;
        updateTransform();
    });
    
    $('#zoom-out').on('click', function() {
        scale /= 1.2;
        if (scale < 0.1) scale = 0.1;
        updateTransform();
    });
    
    $('#reset-zoom').on('click', function() {
        scale = 1;
        translateX = 0;
        translateY = 0;
        updateTransform();
    });
    
    function updateTransform() {
        sagittalImage.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    }
    
    // Drag functionality
    sagittalImage.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
        sagittalImage.style.cursor = 'grabbing';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        updateTransform();
    });
    
    document.addEventListener('mouseup', function() {
        isDragging = false;
        sagittalImage.style.cursor = 'move';
    });
    
    // Mouse wheel zoom
    document.getElementById('sagittal-view').addEventListener('wheel', function(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        scale *= delta;
        if (scale < 0.1) scale = 0.1;
        updateTransform();
    });
    
    // Initialize
    sagittalImage.style.cursor = 'move';
});

// Add the following code at the appropriate location

// Screenshot functionality
function captureScreenshot() {
    const sagittalView = document.getElementById('sagittal-view');
    const sagittalImage = sagittalView.querySelector('img');
    
    // Create a new canvas element
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to current view size
    canvas.width = sagittalView.clientWidth;
    canvas.height = sagittalView.clientHeight;
    
    // Draw current view to canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Get current image transform
    const transform = sagittalImage.style.transform;
    
    // Temporarily apply transform to canvas context
    ctx.save();
    
    // Calculate center point
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // Apply current scale and translation
    ctx.translate(centerX, centerY);
    
    // Extract scale and translation values from transform string
    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    
    if (transform) {
        const scaleMatch = transform.match(/scale\(([^)]+)\)/);
        if (scaleMatch && scaleMatch[1]) {
            scale = parseFloat(scaleMatch[1]);
        }
        
        const translateMatch = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
        if (translateMatch && translateMatch[1] && translateMatch[2]) {
            translateX = parseFloat(translateMatch[1]);
            translateY = parseFloat(translateMatch[2]);
        }
    }
    
    ctx.scale(scale, scale);
    ctx.translate(translateX / scale, translateY / scale);
    
    // Draw image
    ctx.drawImage(sagittalImage, -sagittalImage.width / 2, -sagittalImage.height / 2);
    
    // Restore context
    ctx.restore();
    
    // Convert canvas to image data
    const imageData = canvas.toDataURL('image/png');
    
    // Send to server for saving
    saveScreenshot(imageData);
}

// Save screenshot to server
function saveScreenshot(imageData) {
    fetch('/save_screenshot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            image: imageData,
            filename: currentFilename, // Use correct variable name
            view_type: 'sagittal'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showScreenshotSaved(data.path);
            // Update screenshot list
            loadSavedScreenshots();
        } else {
            alert('Failed to save screenshot: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error saving screenshot:', error);
        alert('Error saving screenshot, please check console');
    });
}

function loadSavedScreenshots() {
    fetch(`/get_screenshots?filename=${encodeURIComponent(currentFilename)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update UI to show saved screenshots here
                console.log('Loaded screenshot list:', data.screenshots);
            }
        })
        .catch(error => {
            console.error('Error loading screenshot list:', error);
        });
}

// Show screenshot saved notification
function showScreenshotSaved(imagePath) {
    const notification = document.createElement('div');
    notification.className = 'screenshot-notification';
    notification.innerHTML = `
        <p>Screenshot saved!</p>
        <img src="${imagePath}" alt="Saved Screenshot" width="150">
        <button id="add-audio-btn" data-screenshot="${imagePath.split('/').pop()}">Add Audio Annotation</button>
    `;
    
    document.body.appendChild(notification);
    
    // Add event listener
    notification.querySelector('#add-audio-btn').addEventListener('click', function() {
        const screenshotFilename = this.getAttribute('data-screenshot');
        showAudioAnnotationDialog(screenshotFilename);
        notification.remove();
    });
    
    // Auto close after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Display audio annotation dialog
function showAudioAnnotationDialog(screenshotFilename) {
    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'audio-annotation-dialog';
    dialog.innerHTML = `
        <h3>Add Audio Annotation to Screenshot</h3>
        <img src="/static/screenshots/${screenshotFilename}" alt="Screenshot" width="200">
        <div class="audio-controls">
            <button id="start-recording">Start Recording</button>
            <button id="stop-recording" disabled>Stop Recording</button>
            <div id="recording-status"></div>
        </div>
        <div class="audio-playback" style="display:none">
            <audio id="audio-playback" controls></audio>
        </div>
        <div class="annotation-text">
            <textarea id="annotation-text" placeholder="Add text annotation (optional)"></textarea>
        </div>
        <div class="dialog-buttons">
            <button id="save-annotation">Save Annotation</button>
            <button id="cancel-annotation">Cancel</button>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    // Recording related variables
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob;
    
    // Add event listeners
    const startRecordingBtn = dialog.querySelector('#start-recording');
    const stopRecordingBtn = dialog.querySelector('#stop-recording');
    const recordingStatus = dialog.querySelector('#recording-status');
    const audioPlayback = dialog.querySelector('.audio-playback');
    const audioPlayer = dialog.querySelector('#audio-playback');
    const saveAnnotationBtn = dialog.querySelector('#save-annotation');
    const cancelAnnotationBtn = dialog.querySelector('#cancel-annotation');
    
    // Start recording
    startRecordingBtn.addEventListener('click', function() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioPlayer.src = audioUrl;
                    audioPlayback.style.display = 'block';
                    recordingStatus.textContent = 'Recording completed';
                });
                
                mediaRecorder.start();
                startRecordingBtn.disabled = true;
                stopRecordingBtn.disabled = false;
                recordingStatus.textContent = 'Recording...';
            })
            .catch(error => {
                console.error('Failed to access microphone:', error);
                recordingStatus.textContent = 'Cannot access microphone';
            });
    });
    
    // Stop recording
    stopRecordingBtn.addEventListener('click', function() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            startRecordingBtn.disabled = false;
            stopRecordingBtn.disabled = true;
        }
    });
    
    // Save annotation
    saveAnnotationBtn.addEventListener('click', function() {
        if (!audioBlob) {
            alert('Please record audio first');
            return;
        }
        
        // Create FormData object to upload audio
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('filename', currentFilename);
        
        // Upload audio file
        fetch('/upload_audio', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Associate audio with screenshot
                const annotationText = dialog.querySelector('#annotation-text').value;
                
                fetch('/associate_audio_with_image', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        screenshot_filename: screenshotFilename,
                        audio_filename: data.filename,
                        annotation_text: annotationText
                    })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        alert('Audio annotation saved');
                        dialog.remove();
                        // Update annotations list
                        loadAnnotations();
                    } else {
                        alert('Failed to save annotation association: ' + result.error);
                    }
                });
            } else {
                alert('Failed to upload audio: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error uploading audio:', error);
            alert('Error uploading audio, please check console');
        });
    });
    
    // Cancel
    cancelAnnotationBtn.addEventListener('click', function() {
        dialog.remove();
    });
}

// Load saved annotations
function loadAnnotations() {
    fetch(`/get_annotations?filename=${encodeURIComponent(currentFilename)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAnnotations(data.annotations);
            }
        })
        .catch(error => {
            console.error('Error loading annotations:', error);
        });
}

// Display annotations list
function displayAnnotations(annotations) {
    const annotationsContainer = document.getElementById('annotations-container');
    if (!annotationsContainer) {
        // Create annotations container
        const container = document.createElement('div');
        container.id = 'annotations-container';
        container.className = 'annotations-container';
        container.innerHTML = '<h3>Saved Annotations</h3><div class="annotations-list"></div>';
        document.querySelector('.viewer-container').appendChild(container);
        annotationsContainer = container;
    }
    
    const annotationsList = annotationsContainer.querySelector('.annotations-list');
    annotationsList.innerHTML = '';
    
    if (annotations.length === 0) {
        annotationsList.innerHTML = '<p>No annotations yet</p>';
        return;
    }
    
    annotations.forEach(annotation => {
        const annotationItem = document.createElement('div');
        annotationItem.className = 'annotation-item';
        annotationItem.innerHTML = `
            <div class="annotation-image">
                <img src="/static/screenshots/${annotation.screenshot}" alt="Screenshot" width="100">
            </div>
            <div class="annotation-content">
                <div class="annotation-audio">
                    <audio controls src="/static/audio/${annotation.audio}"></audio>
                </div>
                <div class="annotation-text">${annotation.text || 'No text annotation'}</div>
                <div class="annotation-timestamp">${new Date(annotation.timestamp).toLocaleString()}</div>
            </div>
        `;
        annotationsList.appendChild(annotationItem);
    });
}

// Add screenshot button after page loads
document.addEventListener('DOMContentLoaded', function() {
    // Add screenshot button to sagittal view
    const sagittalControls = document.createElement('div');
    sagittalControls.className = 'sagittal-controls';
    sagittalControls.innerHTML = `
        <button id="capture-screenshot" title="Screenshot">📷 Screenshot</button>
    `;
    
    const sagittalView = document.getElementById('sagittal-view');
    if (sagittalView) {
        sagittalView.appendChild(sagittalControls);
        
        // Add event listener
        document.getElementById('capture-screenshot').addEventListener('click', captureScreenshot);
    }
    
    // Load saved annotations
    loadAnnotations();
});