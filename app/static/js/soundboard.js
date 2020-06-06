  var array = [];

  function loadArrayFromDict(sounds) {
    function Sound(name, key, keyCode, url){
      this.name = name;
      this.key = key;
      this.code = keyCode;
      this.url = url;
    }
    for (let s of sounds) {
      array.push(new Sound(s.name, s.keyboard_key, s.keyboard_code, s.url))
    }

    buildSoundboard();
  }

  function buildSoundboard(){
    array.forEach(function(sound){
      // add html audio tag
      document.getElementById('audio-container').innerHTML += `<audio data-key="${sound.code}" src="${sound.url}">`;
    })


    const keys = document.querySelectorAll('.soundbutton');
    keys.forEach(key => key.addEventListener('click', clicked));
    keys.forEach(key => key.addEventListener('transitionend', removeTransition));

  }

function clicked(e){
  playSound(this.getAttribute('data-key'));
}

function keyDown(e){
  playSound(e.keyCode);
}

  function playSound(code) {
    const audio = document.querySelector(`audio[data-key="${code}"]`);
    const key = document.querySelector(`.soundbutton[data-key="${code}"]`);
    if (!audio){
      console.log('key not assigned');
      return;
    }
    audio.currentTime = 0;
    audio.play()
    key.classList.add('playing')
  }
  function removeTransition(e){
//    if(e.propertyName !== 'background-color') return; //skip so only fires once
    this.classList.remove('playing');
  }


  window.addEventListener('keydown', keyDown);