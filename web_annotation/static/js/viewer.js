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
            // Update images
            for (let i = 0; i < response.images.length; i++) {
                const imgPath = '/static/images/' + response.images[i] + '?t=' + new Date().getTime();
                $('#image-' + i).attr('src', imgPath);
                $('#slice-info-' + i).text(response.slice_indices[i]);
            }
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

                // 上传音频到后端
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
                        alert('音频上传成功');
                    },
                    error: function() {
                        alert('音频上传失败');
                    }
                });
            };
            $('#record-btn').attr('disabled', true);
            $('#stop-btn').attr('disabled', false);
        })
        .catch(err => {
            alert('无法访问麦克风: ' + err);
        });
});

$('#stop-btn').on('click', function() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        $('#record-btn').attr('disabled', false);
        $('#stop-btn').attr('disabled', true);
        $('#transcribe-btn').prop('disabled', false); // 录音结束后允许转录
    }
});

// 转录按钮事件
$('#transcribe-btn').on('click', function() {
    $('#transcribe-btn').prop('disabled', true);
    $('#transcript-result').text('正在转录...');
    $.ajax({
        url: '/transcribe_audio',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ filename: filename }),
        success: function(response) {
            if (response.success) {
                $('#transcript-result').text('转录结果：' + response.transcript);
            } else {
                $('#transcript-result').text('转录失败：' + (response.error || '未知错误'));
            }
        },
        error: function() {
            $('#transcript-result').text('转录请求失败');
        }
    });
});

// 获取文件名
const filename = document.querySelector('h2').textContent.replace('File: ', '');