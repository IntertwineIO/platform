<template>
  <div id="intertwine__app">

    <IntertwineHeader></IntertwineHeader>
    <router-view/>

    <article class="current_place"><span><i class="fas fa-map-marker-alt"></i> {{ current_place }}</span></article>
    <v-map :zoom="zoom" :center="current">
      <v-tilelayer url="http://{s}.tile.osm.org/{z}/{x}/{y}.png"></v-tilelayer>
      <v-marker :lat-lng="marker"></v-marker>
    </v-map>

  </div>
</template>

<script>
import _ from 'lodash'
import stopPoints from './static/stop_points'
import L from 'leaflet'
const initialPoint = _.find(stopPoints, stop => { return stop.title === 'Austin, TX' })
const initialCoords = initialPoint.coords

export default {
  name: 'App',
  components: {
    IntertwineHeader: () => import('@/components/intertwine_header')
  },
  mounted () {
    setInterval(function () {
      this.getNextMapPoint()
    }.bind(this), 4000)
  },
  data () {
    return {
      stopPoints: stopPoints,
      zoom: 7,
      current: initialCoords,
      current_place: initialPoint.title,
      url: 'http://{s}.tile.osm.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      marker: L.latLng(initialCoords)
    }
  },
  methods: {
    getNextMapPoint () {
      let randomSelection = stopPoints[Math.floor(Math.random() * stopPoints.length)]
      this.current = randomSelection.coords
      this.current_place = randomSelection.title
      this.marker = L.latLng(randomSelection.coords)
    }
  }
}
</script>

<style lang="scss">
@import '~@/sass/palette.scss';
@import '~@/sass/animate.scss';
@import '~@/sass/typog.scss';
@import '~@/sass/_mixins.scss';
@import url('https://fonts.googleapis.com/css?family=Abel|Medula+One');

body {
  @include main_texture;
  margin: 0;
  padding: 0;
  position: relative;
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  a {
    text-decoration: none;
    color: $dark;
    transition: all .3s;
  }

  h1,
  h2,
  h3 {
    color: $red;
    font-family: $header_font;
  }

  h1 {
    font-size: 2.5rem;
  }

  * {
    font-family: $body_font;
  }

  main.stage {
    @include fadeInUp();
    text-align: center;
  }

  button {
    border: none;
    background: transparent;
  }
}

#intertwine__app {
  position: relative;
  height: 100vh;
  width: 100vw;

  .current_place {
    @include accent_texture;
    text-align: center;
    color: #f9be02;
    border-top: 3px solid $gold;

    i {
      color: $gold;
    }

    span {
      display: inline-block;
      color: #f9be02;
      background-color: $red;
      padding: .5rem 3rem;
    }
  }

  .intertwine__map_stage {
    position: relative;
  }

  .vue2leaflet-map {
    border-top: 3px solid $red;
    z-index: 1;
    height: 70vh;
  }
}

</style>
