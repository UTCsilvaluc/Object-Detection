// static/js/api.js

export async function apiPost(url , body){
    try {
        const res = await fetch(url , {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'An error occurred');
        }
        return data;
    } catch (error) {
        console.error("API POST error:", error);
        alert("An error occurred: " + error.message);
        return null;
    }
}
window.apiPost = apiPost;

export function uploadAIImage(lat, lng) {
    const token = crypto.randomUUID();
    if (localStorage) { 
        localStorage.setItem('upload_pending', JSON.stringify({
            token: token,
            latitude: lat,
            longitude: lng
        }));
        const url = `/?token=${token}&latitude=${lat}&longitude=${lng}`;
        window.open(url, '_blank');
    } else {
        alert("Your browser does not support localStorage. Cannot proceed with AI image upload.");
    }
}   
window.uploadAIImage = uploadAIImage;