import Vue from 'vue';
import example from '@/components/example';

describe('example.vue', () => {
  it('should render correct contents', () => {
    const Constructor = Vue.extend(example);
    const vm = new Constructor().$mount();
    expect(vm.$el.querySelector('.hello h1').textContent)
      .to.equal(vm.msg);
  });
});
