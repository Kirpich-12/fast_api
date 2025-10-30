  // Время бездействия в миллисекундах (5 минут)
  console.log('print')
  const INACTIVITY_TIME = 60 * 1000 * 5; 

  let inactivityTimer;

  function resetTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(logoutUser, INACTIVITY_TIME);
  }

  function logoutUser() {
    window.location.href = '/logout';
      console.log('print')
  }

  // События, которые считаются активностью пользователя
  ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'].forEach(event => {
    document.addEventListener(event, resetTimer, false);
  });

  // Запуск таймера при загрузке страницы
  resetTimer();