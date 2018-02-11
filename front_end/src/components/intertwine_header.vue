<template>
  <header class="intertwine__header">
    <figure class="intertwine__logo">
      <router-link :to="{ name: 'home'}">Intertwine</router-link>
    </figure>
    <nav>
      <router-link :to="{ name: 'communities'}">Communities</router-link>
      <router-link :to="{ name: 'problems'}">Problems</router-link>
    </nav>
  </header>
</template>

<style lang="scss" scoped >

.intertwine__header {
  display: flex;
  justify-content: space-between;

  .intertwine__logo {
    padding: 1rem;
    margin: 0;
  }

  nav {
    padding: 1rem;
    margin-right: 2rem;

    a {
      padding: 0 1rem;
    }
  }
}
</style>
