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
@import '~@/sass/palette.scss';

.intertwine__header {
  display: flex;
  justify-content: space-between;
  border-top: 3px solid $light_blue;

  .intertwine__logo {
    padding: 1rem 2rem;
    margin: 0;

    figure {
      color: $red !important;
      a {
        color: $red !important;
      }
    }
  }

  nav {
    margin-right: 2rem;

    a {
      padding: 1rem;
      color: $red;
      display: inline-block;

      &:hover {
        background: $light_blue;
      }
    }
  }
}
</style>
